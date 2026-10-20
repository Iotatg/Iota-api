"""Public Iota songs catalog: search, lookup, random, suggest, file stream."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import Response, StreamingResponse

from app.catalog.audio import demo_wav_bytes
from app.catalog.index import SongIndex
from app.catalog.ip_limit import public_limiter
from app.config import get_settings
from app.dependencies import get_provider, get_stream_proxy
from app.routes.stream import _parse_range
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.services.stream_proxy import StreamProxy
from app.utils.telemetry import telemetry

router = APIRouter()
API_VERSION = "2.0.0"
# Public per-IP rate limit. 0 disables the limit entirely (unlimited);
# override with IOTA_PUBLIC_RPM=<requests per minute> to re-enable. Every
# public route shares one limiter.
PUBLIC_RPM = int(os.environ.get("IOTA_PUBLIC_RPM", "0"))


def _index(request: Request) -> SongIndex:
    idx = getattr(request.app.state, "song_index", None)
    if idx is None:
        idx = SongIndex([])
        request.app.state.song_index = idx
    return idx


def _guard(request: Request) -> None:
    limiter = public_limiter()
    if limiter is not None:
        limiter.check(request)


@router.get("/api/search")
async def api_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50),
):
    _guard(request)
    results = _index(request).search(q, limit=limit)
    return {
        "success": True,
        "total_results": len(results),
        "query": q,
        "hint": "Use /api/song/{video_id} or stream via stream_url" if results else "No matches.",
        "results": results,
    }


@router.get("/api/song/{video_id}")
async def api_song(request: Request, video_id: str = Path(..., min_length=1, max_length=32)):
    _guard(request)
    song = _index(request).get(video_id)
    if not song:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": "Not Found",
                "code": "SONG_NOT_FOUND",
                "message": f"Song '{video_id}' is not in the Iota catalog.",
            },
        )
    return {"success": True, "hint": "Stream using stream_url.", "song": song}


@router.get("/api/random")
async def api_random(request: Request, limit: int = Query(10, ge=1, le=50)):
    _guard(request)
    sampled = _index(request).random(limit)
    return {
        "success": True,
        "total_results": len(sampled),
        "query": "random",
        "hint": "Call again for a fresh shuffle.",
        "results": sampled,
    }


@router.get("/api/songs")
async def api_songs(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    _guard(request)
    payload = _index(request).page(page=page, limit=limit)
    payload["success"] = True
    payload["hint"] = (
        f"Next page /api/songs?page={page + 1}&limit={limit}"
        if page < payload["total_pages"]
        else "Last page."
    )
    return payload


@router.get("/api/suggest")
async def api_suggest(request: Request, q: str = Query(..., min_length=1, max_length=80)):
    _guard(request)
    suggestions = _index(request).suggest(q)
    # Enrich local-catalog hits with live titles (Deezer). Best-effort:
    # any upstream failure silently degrades to local-only suggestions.
    from app.services.discovery import get_shared_client
    live = await get_shared_client(request).suggest(q, limit=10)
    seen = {s.lower().strip() for s in suggestions}
    for s in live:
        if s.lower().strip() not in seen:
            suggestions.append(s)
            seen.add(s.lower().strip())
    return {"success": True, "query": q, "suggestions": suggestions[:10]}


@router.get("/api/trending")
async def api_trending(request: Request, limit: int = Query(10, ge=1, le=50)):
    """The most played entries of the curated catalog.

    The catalog holds no view counter, so the order is the curated one and
    not a live chart. The live chart is served by the key protected
    /trending route.
    """
    _guard(request)
    results = _index(request).trending(limit)
    return {
        "success": True,
        "total_results": len(results),
        "source": "catalog",
        "hint": "The curated catalog in its curated order, /trending serves the live chart.",
        "results": results,
    }


@router.get("/api/stats")
async def api_catalog_stats(request: Request):
    stats = _index(request).stats()
    return {
        "success": True,
        "status": "healthy",
        "version": API_VERSION,
        "rate_limit_per_minute": PUBLIC_RPM,
        "hint": "Visit /docs for the live scratchpad.",
        **stats,
    }


@router.get("/api/status")
@router.get("/api/stats/live")
async def api_live_stats(request: Request):
    """Live usage telemetry for the /status page: streams, downloads,
    searches, latency percentiles, per-provider health, top tracks and a
    rolling event feed. Counters are public-safe — no keys, no exact
    client addresses are exposed."""
    from app.config import get_settings

    snap = telemetry.snapshot()
    snap.update({
        "success": True,
        "version": API_VERSION,
        "rate_limit_per_minute": PUBLIC_RPM,
        "catalog_total": _index(request).stats().get("total_songs", 0),
        "redis": get_settings().redis_disabled is False,
    })
    return snap


@router.get("/api")
async def api_root():
    return {
        "name": "iota-api",
        "version": API_VERSION,
        "products": ["songs", "iotadb"],
        "docs": "/docs",
        "health": "/health",
        "db": "/db",
        "endpoints": {
            "search": "/api/search?q={query}&limit=10",
            "song": "/api/song/{video_id}",
            "random": "/api/random?limit=10",
            "songs": "/api/songs?page=1&limit=50",
            "suggest": "/api/suggest?q={prefix}",
            "trending": "/api/trending",
            "stats": "/api/stats",
            "file": "/api/file/{video_id}",
            "stream": "/stream/{media_id}",
            "download": "/download/{media_id}?kind=audio|video",
            "iotadb": "/api/v1/db/{collection}/find",
        },
    }


@router.get("/api/file/{video_id}")
async def api_file(
    request: Request,
    video_id: str = Path(..., min_length=1, max_length=32),
    range_header: Optional[str] = Header(default=None, alias="Range"),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
):
    _guard(request)
    song = _index(request).get(video_id)
    if not song:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "Unknown track."})
    # Real provider-backed tracks stream the actual audio from the
    # provider (YouTube). Demo tracks keep the synthetic WAV so the
    # catalog stays playable even with no upstream access.
    if song.get("source") == "youtube":
        return await _proxy_real_audio(
            video_id, range_header, stream_proxy, provider,
            client_ip=request.client.host if request.client else None,
        )
    return _demo_wav_response(video_id, range_header)


def _demo_wav_response(video_id: str, range_header: Optional[str]) -> Response:
    """Serve the synthetic demo WAV for non-provider tracks."""
    body = demo_wav_bytes(video_id, seconds=2.0)
    size = len(body)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "audio/wav",
        "Cache-Control": "public, max-age=3600",
    }
    if range_header and range_header.startswith("bytes="):
        spec = range_header[6:]
        start_s, _, end_s = spec.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else size - 1
        start = max(0, start)
        end = min(size - 1, end)
        if start > end:
            raise HTTPException(status_code=416, detail={"error": "range_not_satisfiable"})
        chunk = body[start : end + 1]
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(len(chunk))
        return Response(content=chunk, status_code=206, headers=headers, media_type="audio/wav")
    headers["Content-Length"] = str(size)
    return StreamingResponse(iter([body]), media_type="audio/wav", headers=headers)


async def _proxy_real_audio(
    video_id: str,
    range_header: Optional[str],
    stream_proxy: StreamProxy,
    provider: MediaProvider,
    client_ip: Optional[str] = None,
) -> StreamingResponse:
    """Stream real audio for a catalog track via the provider.

    Only IDs present in the curated catalog reach this path (the
    route 404s anything else), so this is not an open proxy. The
    provider resolves the YouTube id to a CDN URL and the stream
    proxy relays the bytes with HTTP Range support.
    """
    import time as _time

    _setup_started = _time.perf_counter()
    media_id = f"yt:{video_id}"
    try:
        src = await provider.get_stream_by_type(media_id, "audio")
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "media_not_found", "detail": "Track unavailable."})
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={"error": "provider_unavailable", "detail": str(e)})
    except ProviderError as e:
        raise HTTPException(status_code=502, detail={"error": "provider_error", "detail": str(e)})

    if not src.direct_url:
        raise HTTPException(status_code=502, detail={"error": "no_stream_url", "detail": "Provider returned no stream URL."})

    try:
        head = await stream_proxy.head(src.direct_url)
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=502, detail={"error": "upstream_unavailable", "detail": str(e)})

    size = head.size_bytes or 0
    mime_type = head.content_type or src.mime_type or "audio/mp4"

    start, end, status_code, content_range = 0, size - 1, 200, None
    if range_header:
        parsed = _parse_range(range_header, size)
        if parsed is not None:
            start, end = parsed
            status_code = 206
            content_range = f"bytes {start}-{end}/{size}"
    content_length = end - start + 1

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Cache-Control": "public, max-age=300",
        "X-Content-Type-Options": "nosniff",
    }
    if content_range:
        headers["Content-Range"] = content_range

    settings = get_settings()
    chunk_size = settings.stream_chunk_size
    workers = settings.stream_parallel_workers
    direct_url = src.direct_url
    telemetry.record_latency(
        (_time.perf_counter() - _setup_started) * 1000, provider="YouTube"
    )
    telemetry.record_stream_start(
        media_id, title=video_id, provider="yt", client_ip=client_ip
    )

    async def body():
        sent = 0
        if workers > 1:
            stream_iter = stream_proxy.stream_parallel(
                direct_url, start=start, end=end,
                chunk_size=chunk_size, workers=workers,
            )
        else:
            stream_iter = stream_proxy.stream(
                direct_url, start=start, end=end, chunk_size=chunk_size,
            )
        try:
            async for chunk in stream_iter:
                sent += len(chunk)
                yield chunk
        finally:
            telemetry.record_stream_bytes(media_id, sent, provider="yt")

    return StreamingResponse(body(), status_code=status_code, headers=headers, media_type=mime_type)
