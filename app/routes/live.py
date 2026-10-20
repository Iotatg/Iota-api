"""Public live search + playback over the provider registry.

Zero-key, IP-rate-limited surface that lets the landing page search and
play ANY track the providers know — not just the small curated catalog.
Same trust model as ``/api/file``: this service resolves and proxies the
bytes itself. To keep it from becoming an open proxy, playback is limited
to media ids that this IP session just received from ``/api/live``
(15-minute allowlist, bounded memory).
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import StreamingResponse

from app.catalog.ip_limit import public_limiter
from app.dependencies import get_provider, get_stream_proxy
from app.routes.stream import _parse_range
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.services.stream_proxy import StreamProxy
from app.utils.logging import get_logger
from app.utils.telemetry import telemetry, provider_of

logger = get_logger(__name__)

router = APIRouter()
# Public per-IP rate limit. 0 disables the limit entirely (unlimited);
# override with IOTA_PUBLIC_RPM=<requests per minute> to re-enable. Every
# public route shares one limiter.

RECENT_TTL_SECONDS = 900
MAX_TRACKED_IPS = 4096
# Every prefix a provider can return, see app/services/provider_registry.py.
_IP_PREFIXES = ("yt:", "dz:", "am:", "sp:", "mb:", "jv:", "sc:", "bp:", "rs:")


def _guard(request: Request) -> None:
    limiter = public_limiter()
    if limiter is not None:
        limiter.check(request)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class _SessionAllowlist:
    """ip -> {media_id: last_seen_ts}. Bounded, TTL-evicted."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, float]] = {}
        self._lock = asyncio.Lock()

    async def remember(self, ip: str, media_ids: list[str]) -> None:
        if not media_ids:
            return
        async with self._lock:
            bucket = self._data.setdefault(ip, {})
            now = time.time()
            for mid in media_ids:
                bucket[mid] = now
            if len(self._data) > MAX_TRACKED_IPS:
                for stale in sorted(
                    self._data, key=lambda k: min(self._data[k].values())
                )[: len(self._data) - MAX_TRACKED_IPS // 2]:
                    self._data.pop(stale, None)

    async def allows(self, ip: str, media_id: str) -> bool:
        async with self._lock:
            bucket = self._data.get(ip)
            if not bucket:
                return False
            ts = bucket.get(media_id)
            if ts is None:
                return False
            if time.time() - ts > RECENT_TTL_SECONDS:
                bucket.pop(media_id, None)
                return False
            return True


_sessions = _SessionAllowlist()


def _looks_like_media_id(value: str) -> bool:
    return any(value.startswith(p) for p in _IP_PREFIXES)


@router.get("/api/live")
async def api_live(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    provider: MediaProvider = Depends(get_provider),
):
    """Live provider search for any song — no API key, IP rate-limited."""
    _guard(request)
    started = time.perf_counter()
    try:
        results = await provider.search(q, limit=limit)
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": str(e)})
    except ProviderError as e:
        raise HTTPException(status_code=502, detail={
            "error": "provider_error", "detail": str(e)})

    items = [
        {
            "media_id": m.media_id,
            "title": m.title,
            "artist": m.artist,
            "duration_seconds": m.duration_seconds,
            "thumbnail_url": m.thumbnail_url,
            "size_bytes": m.size_bytes,
            "mime_type": m.mime_type,
            "provider": m.provider,
            "views": m.views,
            "likes": m.likes,
            "play_url": f"/api/live-play/{m.media_id}",
        }
        for m in results
    ]
    await _sessions.remember(_client_ip(request), [i["media_id"] for i in items])
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    telemetry.record_search(q, elapsed_ms, client_ip=_client_ip(request))
    for m in results:
        telemetry.note_fetch(m.media_id, m.title, getattr(m, "provider", "") or "")
    return {
        "success": True,
        "query": q,
        "count": len(items),
        "elapsed_ms": elapsed_ms,
        "results": items,
    }


@router.get("/api/live-play/{media_id:path}")
async def api_live_play(
    request: Request,
    media_id: str = Path(..., min_length=1, max_length=64),
    range_header: Optional[str] = Header(default=None, alias="Range"),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
) -> StreamingResponse:
    """Stream audio for a media id just returned by /api/live.

    Not an open proxy: only ids this IP session recently searched are
    playable (see _SessionAllowlist). Range/206 supported.
    """
    _guard(request)
    started = time.perf_counter()

    if not _looks_like_media_id(media_id) or not await _sessions.allows(
        _client_ip(request), media_id
    ):
        telemetry.note_blocked()
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": "Search for this track first — playback is session-scoped.",
        })

    try:
        src = await provider.get_stream(media_id)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found", "detail": "Track unavailable."})
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": str(e)})
    except ProviderError as e:
        raise HTTPException(status_code=502, detail={
            "error": "provider_error", "detail": str(e)})

    if not src.direct_url:
        raise HTTPException(status_code=502, detail={
            "error": "no_stream_url", "detail": "Provider returned no stream URL."})

    try:
        head = await stream_proxy.head(src.direct_url)
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=502, detail={
            "error": "upstream_unavailable", "detail": str(e)})

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
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if content_range:
        headers["Content-Range"] = content_range

    from app.config import get_settings

    settings = get_settings()
    chunk_size = settings.stream_chunk_size
    workers = settings.stream_parallel_workers
    direct_url = src.direct_url
    prov = provider_of(media_id)
    telemetry.record_latency((time.perf_counter() - started) * 1000, provider=prov)
    telemetry.record_stream_start(media_id, client_ip=_client_ip(request), provider=prov)

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
        except ProviderUnavailableError:
            telemetry.note_error("upstream_died", provider=prov)
            logger.info("live_play_upstream_died", extra={"media_id": media_id})
            raise
        finally:
            telemetry.record_stream_bytes(media_id, sent, provider=prov)

    return StreamingResponse(
        body(), status_code=status_code, headers=headers, media_type=mime_type
    )
