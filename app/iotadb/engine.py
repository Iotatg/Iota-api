"""IotaDB tenant engine: collections, documents, keys, files, IP allowlist."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import secrets
import time
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.iotadb.query import apply_query, cosine_similarity, run_aggregation, sanitize_query
from app.models.iotadb import (
    IotaCollection,
    IotaDocument,
    IotaIpEntry,
    IotaLiveKey,
    IotaStoredFile,
    IotaTenant,
)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _loads(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _dumps(obj: Any) -> str:
    return json.dumps(obj, default=str, separators=(",", ":"))


def _public_doc(doc: IotaDocument) -> dict[str, Any]:
    payload = _loads(doc.payload)
    if not isinstance(payload, dict):
        payload = {}
    payload["id"] = doc.id
    payload["_created_at"] = doc.created_at
    payload["_updated_at"] = doc.updated_at
    return payload


class IotaDBEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_tenant(self, user_id: str, username: str = "sandbox") -> IotaTenant:
        row = await self.session.get(IotaTenant, user_id)
        if row:
            return row
        row = IotaTenant(user_id=user_id, username=username, name=username)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_collection(self, user_id: str, name: str) -> dict[str, Any]:
        await self.ensure_tenant(user_id)
        clean = name.strip().lower()
        existing = (
            await self.session.execute(
                select(IotaCollection).where(
                    IotaCollection.user_id == user_id, IotaCollection.name == clean
                )
            )
        ).scalar_one_or_none()
        if existing:
            return {"name": existing.name, "created_at": existing.created_at}
        coll = IotaCollection(user_id=user_id, name=clean, created_at=time.time())
        self.session.add(coll)
        await self.session.flush()
        return {"name": coll.name, "created_at": coll.created_at}

    async def list_collections(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(IotaCollection).where(IotaCollection.user_id == user_id).order_by(IotaCollection.name)
            )
        ).scalars().all()
        out = []
        for c in rows:
            docs = (
                await self.session.execute(
                    select(IotaDocument).where(
                        IotaDocument.user_id == user_id, IotaDocument.collection == c.name
                    )
                )
            ).scalars().all()
            out.append({"name": c.name, "created_at": c.created_at, "count": len(docs)})
        return out

    async def drop_collection(self, user_id: str, name: str) -> bool:
        clean = name.strip().lower()
        docs = (
            await self.session.execute(
                select(IotaDocument).where(
                    IotaDocument.user_id == user_id, IotaDocument.collection == clean
                )
            )
        ).scalars().all()
        for d in docs:
            await self.session.delete(d)
        coll = (
            await self.session.execute(
                select(IotaCollection).where(
                    IotaCollection.user_id == user_id, IotaCollection.name == clean
                )
            )
        ).scalar_one_or_none()
        if not coll:
            return False
        await self.session.delete(coll)
        await self.session.flush()
        return True

    async def insert(self, user_id: str, collection: str, doc_data: dict[str, Any]) -> dict[str, Any]:
        name = collection.strip().lower()
        await self.create_collection(user_id, name)
        clean = sanitize_query(doc_data if isinstance(doc_data, dict) else {})
        if not isinstance(clean, dict):
            clean = {}
        now = time.time()
        doc_id = secrets.token_hex(12)
        row = IotaDocument(
            id=doc_id,
            user_id=user_id,
            collection=name,
            payload=_dumps(clean),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        return _public_doc(row)

    async def _docs(self, user_id: str, collection: str) -> list[IotaDocument]:
        name = collection.strip().lower()
        rows = (
            await self.session.execute(
                select(IotaDocument).where(
                    IotaDocument.user_id == user_id, IotaDocument.collection == name
                )
            )
        ).scalars().all()
        return list(rows)

    async def find(
        self,
        user_id: str,
        collection: str,
        query: dict[str, Any] | None = None,
        limit: int = 50,
        skip: int = 0,
        sort_field: str = "_created_at",
        sort_order: int = -1,
    ) -> list[dict[str, Any]]:
        rows = await self._docs(user_id, collection)
        public = [_public_doc(r) for r in rows]
        matched = apply_query(public, query)
        reverse = int(sort_order) < 0
        matched.sort(key=lambda d: d.get(sort_field, 0), reverse=reverse)
        start = max(0, int(skip))
        end = start + max(1, min(int(limit), 200))
        return matched[start:end]

    async def get(self, user_id: str, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        row = await self.session.get(IotaDocument, doc_id)
        if not row or row.user_id != user_id or row.collection != collection.strip().lower():
            return None
        return _public_doc(row)

    async def update(
        self, user_id: str, collection: str, doc_id: str, update_data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        row = await self.session.get(IotaDocument, doc_id)
        if not row or row.user_id != user_id or row.collection != collection.strip().lower():
            return None
        payload = _loads(row.payload)
        if not isinstance(payload, dict):
            payload = {}
        clean = sanitize_query(update_data if isinstance(update_data, dict) else {})
        if isinstance(clean, dict):
            payload.update(clean)
        row.payload = _dumps(payload)
        row.updated_at = time.time()
        await self.session.flush()
        return _public_doc(row)

    async def delete(self, user_id: str, collection: str, doc_id: str) -> bool:
        row = await self.session.get(IotaDocument, doc_id)
        if not row or row.user_id != user_id or row.collection != collection.strip().lower():
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def aggregate(
        self, user_id: str, collection: str, pipeline: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = await self._docs(user_id, collection)
        public = [_public_doc(r) for r in rows]
        return run_aggregation(public, pipeline)

    async def vector_search(
        self,
        user_id: str,
        collection: str,
        query_vector: list[float],
        vector_field: str = "embedding",
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        rows = await self._docs(user_id, collection)
        scored = []
        for r in rows:
            d = _public_doc(r)
            vec = d.get(vector_field)
            if isinstance(vec, list) and len(vec) == len(query_vector):
                try:
                    score = cosine_similarity([float(x) for x in vec], [float(x) for x in query_vector])
                except (TypeError, ValueError):
                    continue
                d["_similarity_score"] = round(score, 4)
                scored.append(d)
        scored.sort(key=lambda x: x.get("_similarity_score", 0), reverse=True)
        return scored[: max(1, min(int(top_k), 50))]

    async def create_api_key(
        self,
        user_id: str,
        key_name: str = "Live Key",
        scopes: list[str] | None = None,
        allowed_ips: list[str] | None = None,
    ) -> dict[str, Any]:
        await self.ensure_tenant(user_id)
        raw = f"iota_live_{secrets.token_urlsafe(32)}"
        key_id = f"key_{secrets.token_hex(6)}"
        now = time.time()
        row = IotaLiveKey(
            key_id=key_id,
            user_id=user_id,
            name=key_name,
            key_hash=_hash_key(raw),
            key_prefix=raw[:12] + "..." + raw[-4:],
            scopes=_dumps(scopes or ["read", "write", "storage"]),
            allowed_ips=_dumps(allowed_ips or ["0.0.0.0/0"]),
            created_at=now,
            is_active=True,
        )
        self.session.add(row)
        await self.session.flush()
        return {
            "key_id": key_id,
            "user_id": user_id,
            "name": key_name,
            "key_prefix": row.key_prefix,
            "scopes": scopes or ["read", "write", "storage"],
            "allowed_ips": allowed_ips or ["0.0.0.0/0"],
            "created_at": now,
            "raw_key": raw,
        }

    async def list_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(IotaLiveKey).where(IotaLiveKey.user_id == user_id, IotaLiveKey.is_active.is_(True))
            )
        ).scalars().all()
        return [
            {
                "key_id": k.key_id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": _loads(k.scopes),
                "allowed_ips": _loads(k.allowed_ips),
                "created_at": k.created_at,
                "last_used_at": k.last_used_at,
            }
            for k in rows
        ]

    async def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        row = await self.session.get(IotaLiveKey, key_id)
        if not row or row.user_id != user_id:
            return False
        row.is_active = False
        await self.session.flush()
        return True

    async def authenticate_api_key(self, raw_key: str, client_ip: str = "0.0.0.0") -> Optional[dict[str, Any]]:
        if not raw_key:
            return None
        digest = _hash_key(raw_key.strip())
        row = (
            await self.session.execute(
                select(IotaLiveKey).where(IotaLiveKey.key_hash == digest, IotaLiveKey.is_active.is_(True))
            )
        ).scalar_one_or_none()
        if not row:
            return None
        allowed = _loads(row.allowed_ips) or ["0.0.0.0/0"]
        if not _ip_allowed(client_ip, allowed):
            return None
        row.last_used_at = time.time()
        tenant = await self.session.get(IotaTenant, row.user_id)
        if tenant:
            tenant.api_calls_count = int(tenant.api_calls_count or 0) + 1
        await self.session.flush()
        return {
            "key_id": row.key_id,
            "user_id": row.user_id,
            "scopes": _loads(row.scopes),
        }

    async def dashboard_stats(self, user_id: str) -> dict[str, Any]:
        tenant = await self.ensure_tenant(user_id)
        colls = await self.list_collections(user_id)
        docs = (
            await self.session.execute(
                select(IotaDocument).where(IotaDocument.user_id == user_id)
            )
        ).scalars().all()
        keys = await self.list_api_keys(user_id)
        files = (
            await self.session.execute(
                select(IotaStoredFile).where(IotaStoredFile.user_id == user_id)
            )
        ).scalars().all()
        return {
            "user_id": user_id,
            "username": tenant.username,
            "name": tenant.name,
            "total_collections": len(colls),
            "total_documents": len(docs),
            "total_files": len(files),
            "total_api_calls": tenant.api_calls_count,
        }

    async def record_file(
        self, user_id: str, filename: str, size: int, mimetype: str, storage_key: str
    ) -> dict[str, Any]:
        uid = secrets.token_hex(12)
        row = IotaStoredFile(
            uid=uid,
            user_id=user_id,
            filename=filename,
            size=size,
            mimetype=mimetype or "application/octet-stream",
            storage_key=storage_key,
            created_at=time.time(),
        )
        self.session.add(row)
        await self.session.flush()
        return {
            "uid": uid,
            "filename": filename,
            "size": size,
            "mimetype": row.mimetype,
            "url": f"/api/v1/storage/file/{uid}",
            "created_at": row.created_at,
        }

    async def list_files(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(IotaStoredFile)
                .where(IotaStoredFile.user_id == user_id)
                .order_by(IotaStoredFile.created_at.desc())
            )
        ).scalars().all()
        return [
            {
                "uid": f.uid,
                "filename": f.filename,
                "size": f.size,
                "mimetype": f.mimetype,
                "url": f"/api/v1/storage/file/{f.uid}",
                "created_at": f.created_at,
            }
            for f in rows[: max(1, min(int(limit), 200))]
        ]

    async def get_file(self, user_id: str | None, uid: str) -> Optional[IotaStoredFile]:
        row = await self.session.get(IotaStoredFile, uid)
        if not row:
            return None
        if user_id is not None and row.user_id != user_id:
            return None
        return row

    async def delete_file(self, user_id: str, uid: str) -> bool:
        row = await self.get_file(user_id, uid)
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def add_ip(self, user_id: str, ip: str, comment: str = "") -> dict[str, Any]:
        clean = ip.strip()
        try:
            ipaddress.ip_network(clean, strict=False)
        except Exception:
            return {"error": "Invalid IP address or CIDR format."}
        existing = (
            await self.session.execute(
                select(IotaIpEntry).where(IotaIpEntry.user_id == user_id, IotaIpEntry.ip == clean)
            )
        ).scalar_one_or_none()
        if existing:
            return {"error": "IP already exists in access list"}
        entry_id = f"ip_{secrets.token_hex(6)}"
        row = IotaIpEntry(
            entry_id=entry_id,
            user_id=user_id,
            ip=clean,
            comment=comment.strip() or "Allow access",
            status="active",
            created_at=time.time(),
        )
        self.session.add(row)
        await self.session.flush()
        return {"entry_id": entry_id, "ip": clean, "comment": row.comment, "status": "active"}

    async def list_ips(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(IotaIpEntry).where(IotaIpEntry.user_id == user_id)
            )
        ).scalars().all()
        if not rows:
            created = await self.add_ip(user_id, "0.0.0.0/0", "Allow access from anywhere")
            return [created]
        return [
            {"entry_id": r.entry_id, "ip": r.ip, "comment": r.comment, "status": r.status}
            for r in rows
        ]

    async def remove_ip(self, user_id: str, entry_id: str) -> bool:
        row = await self.session.get(IotaIpEntry, entry_id)
        if not row or row.user_id != user_id:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


def _ip_allowed(client_ip: str, allowed: list[str]) -> bool:
    if not allowed or "0.0.0.0/0" in allowed:
        return True
    try:
        addr = ipaddress.ip_address(client_ip)
    except Exception:
        return False
    for item in allowed:
        try:
            net = ipaddress.ip_network(item, strict=False)
            if addr in net:
                return True
        except Exception:
            if item == client_ip:
                return True
    return False
