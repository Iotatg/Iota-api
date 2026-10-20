"""IotaDB HTTP API: collections, documents, keys, storage, IP allowlist."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.iotadb.engine import IotaDBEngine
from app.services.storage import ObjectNotFoundError, StorageService

router = APIRouter()
SANDBOX_USER = "usr_sandbox_public"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


async def get_ctx(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
):
    """Resolve the tenant of a request.

    Every route needs a key. The public sandbox is only reachable through the
    anonymous key endpoint, which mints a key for the sandbox tenant. Without
    a key no document of any tenant can be read or written.
    """
    engine = IotaDBEngine(session)
    raw = x_api_key
    if not raw and authorization:
        raw = authorization[7:].strip() if authorization.lower().startswith("bearer ") else authorization
    if raw and raw.startswith("iota_live_"):
        key = await engine.authenticate_api_key(raw, _client_ip(request))
        if not key:
            raise HTTPException(status_code=401, detail={"error": "invalid_api_key", "detail": "IotaDB key rejected."})
        return {"user_id": key["user_id"], "engine": engine, "auth": "api_key"}
    raise HTTPException(
        status_code=401,
        detail={
            "error": "missing_api_key",
            "detail": "Provide an IotaDB key via the X-API-Key header or Authorization: Bearer. "
                      "A sandbox key is minted with POST /api/v1/keys/anonymous.",
        },
    )


def _storage(request: Request) -> StorageService:
    return request.app.state.storage


@router.post("/api/v1/keys/anonymous")
@router.post("/api/v1/auth/anonymous-key")
async def anonymous_key(session: AsyncSession = Depends(get_session)):
    engine = IotaDBEngine(session)
    await engine.ensure_tenant(SANDBOX_USER, "sandbox")
    key = await engine.create_api_key(SANDBOX_USER, "Sandbox Key")
    await session.commit()
    return key


@router.get("/api/v1/db/stats")
async def db_stats(ctx=Depends(get_ctx)):
    return await ctx["engine"].dashboard_stats(ctx["user_id"])


@router.get("/api/v1/db/collections")
async def list_collections(ctx=Depends(get_ctx)):
    return await ctx["engine"].list_collections(ctx["user_id"])


@router.post("/api/v1/db/collections")
async def create_collection(payload: dict[str, Any], ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    name = str(payload.get("name") or "")
    if not name:
        raise HTTPException(status_code=400, detail={"error": "name_required"})
    out = await ctx["engine"].create_collection(ctx["user_id"], name)
    await session.commit()
    return out


@router.post("/api/v1/db/{collection}/insert")
async def insert_doc(collection: str, payload: dict[str, Any], ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    out = await ctx["engine"].insert(ctx["user_id"], collection, payload)
    await session.commit()
    return out


@router.post("/api/v1/db/{collection}/find")
async def find_docs(collection: str, payload: dict[str, Any] | None = None, ctx=Depends(get_ctx)):
    body = payload or {}
    query = body.get("query", body)
    limit = int(body.get("limit", 50))
    skip = int(body.get("skip", 0))
    return await ctx["engine"].find(ctx["user_id"], collection, query, limit=limit, skip=skip)


@router.post("/api/v1/db/{collection}/aggregate")
async def aggregate_docs(collection: str, payload: dict[str, Any], ctx=Depends(get_ctx)):
    pipeline = payload.get("pipeline") or payload.get("stages") or []
    try:
        return await ctx["engine"].aggregate(ctx["user_id"], collection, pipeline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "bad_pipeline", "detail": str(e)})


@router.post("/api/v1/db/{collection}/vector-search")
async def vector_search(collection: str, payload: dict[str, Any], ctx=Depends(get_ctx)):
    vec = payload.get("vector") or payload.get("embedding") or []
    field = payload.get("vector_field", "embedding")
    top_k = int(payload.get("top_k", 10))
    return await ctx["engine"].vector_search(ctx["user_id"], collection, vec, field, top_k)


@router.get("/api/v1/db/keys")
async def list_keys(ctx=Depends(get_ctx)):
    return await ctx["engine"].list_api_keys(ctx["user_id"])


@router.post("/api/v1/db/keys")
async def create_key(payload: dict[str, Any] | None = None, ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    body = payload or {}
    out = await ctx["engine"].create_api_key(ctx["user_id"], str(body.get("name") or "Live Key"))
    await session.commit()
    return out


@router.delete("/api/v1/db/keys/{key_id}")
async def revoke_key(key_id: str, ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    ok = await ctx["engine"].revoke_api_key(ctx["user_id"], key_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    await session.commit()
    return {"ok": True}


@router.get("/api/v1/db/{collection}/{doc_id}")
async def get_doc(collection: str, doc_id: str, ctx=Depends(get_ctx)):
    doc = await ctx["engine"].get(ctx["user_id"], collection, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return doc


@router.put("/api/v1/db/{collection}/{doc_id}")
async def update_doc(collection: str, doc_id: str, payload: dict[str, Any], ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    doc = await ctx["engine"].update(ctx["user_id"], collection, doc_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    await session.commit()
    return doc


@router.delete("/api/v1/db/{collection}/{doc_id}")
async def delete_doc(collection: str, doc_id: str, ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    ok = await ctx["engine"].delete(ctx["user_id"], collection, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    await session.commit()
    return {"ok": True}


@router.get("/api/v1/network/ips")
async def list_ips(ctx=Depends(get_ctx)):
    return await ctx["engine"].list_ips(ctx["user_id"])


@router.post("/api/v1/network/ips")
async def add_ip(payload: dict[str, Any], ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    out = await ctx["engine"].add_ip(ctx["user_id"], str(payload.get("ip") or ""), str(payload.get("comment") or ""))
    await session.commit()
    return out


@router.delete("/api/v1/network/ips/{entry_id}")
async def remove_ip(entry_id: str, ctx=Depends(get_ctx), session: AsyncSession = Depends(get_session)):
    ok = await ctx["engine"].remove_ip(ctx["user_id"], entry_id)
    await session.commit()
    return {"ok": ok}


@router.post("/api/v1/storage/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    ctx=Depends(get_ctx),
    session: AsyncSession = Depends(get_session),
):
    storage = _storage(request)
    data = await file.read()
    if len(data) > 32 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"error": "file_too_large", "detail": "Max 32MB in this build."})
    tmp = Path("/tmp/opencode") / f"iota-{file.filename or 'upload.bin'}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    rec = await ctx["engine"].record_file(
        ctx["user_id"],
        file.filename or "upload.bin",
        len(data),
        file.content_type or "application/octet-stream",
        "",
    )
    key = f"iotadb/{ctx['user_id']}/{rec['uid']}"
    await storage.put(key, str(tmp))
    rec["storage_key"] = key
    from app.models.iotadb import IotaStoredFile
    row = await session.get(IotaStoredFile, rec["uid"])
    if row:
        row.storage_key = key
    await session.commit()
    rec["url"] = f"/api/v1/storage/file/{rec['uid']}"
    return rec


@router.get("/api/v1/storage/files")
async def list_files(ctx=Depends(get_ctx)):
    return await ctx["engine"].list_files(ctx["user_id"])


@router.get("/api/v1/storage/file/{uid}")
async def stream_file(uid: str, request: Request, ctx=Depends(get_ctx)):
    row = await ctx["engine"].get_file(None, uid)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    storage = _storage(request)
    try:
        size = await storage.size(row.storage_key)
    except ObjectNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    start, end = 0, size - 1
    status_code = 200
    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        spec = range_header[6:]
        a, _, b = spec.partition("-")
        start = int(a) if a else 0
        end = int(b) if b else size - 1
        status_code = 206
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Type": row.mimetype,
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    async def gen():
        async for chunk in storage.open_stream(row.storage_key, start, end):
            yield chunk

    return StreamingResponse(gen(), status_code=status_code, headers=headers, media_type=row.mimetype)
