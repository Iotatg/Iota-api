"""Streaming endpoint with HTTP Range support.

GET  /stream/{media_id}  — stream audio
HEAD /stream/{media_id}  — headers only (same as GET without body)

Implements the streaming rules from RFC 9110:
- 200 OK with full body if no Range header
- 206 Partial Content with `Content-Range` if Range present
- Always: `Accept-Ranges: bytes` (advertises support)
- `Content-Length` set correctly for both 200 and 206

Authentication: requires a valid API key (query or header).
Rate limiting: per-minute + daily + concurrent stream slots.
"""
from __future__ import annotations

import re
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import require_api_key, touch
from app.config import get_settings
from app.database import get_session
from app.dependencies import (
    get_provider,
    get_rate_limiter,
    get_storage,
    get_stream_proxy,
)
from app.models.api_key import APIKey
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.services.storage import ObjectNotFoundError, StorageService
from app.services.audio_fix import FIX_FORMATS, ensure_fixed_source
from app.services.stream_fallback import relay_source
from app.services.stream_proxy import StreamProxy
from app.utils.logging import get_logger
from app.utils.metrics import (
    active_streams,
    api_request_duration_seconds,
    stream_bytes_total,
)
from app.utils.rate_limit import RateLimiter

logger = get_logger(__name__)
router = APIRouter()

_EXT_BY_MIME = {
    "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
    "audio/webm": "webm", "audio/ogg": "ogg", "video/mp4": "mp4",
}


def _ext_for(mime: str) -> str:
    return _EXT_BY_MIME.get((mime or "").split(";")[0].strip(), "bin")

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _parse_range(header: str, size: int) -> Optional[tuple[int, int]]:
    """Parse an HTTP Range header. Returns (start, end_inclusive) or None.

    Returns None if the header is malformed (we then serve full body, per
    RFC 9110 §14.1.2). Raises HTTPException 416 if the range is unsatisfiable.
    """
    m = _RANGE_RE.match(header.strip())
    if not m:
        return None
    start_s, end_s = m.group(1), m.group(2)

    if not start_s and not end_s:
        raise HTTPException(status_code=416, detail={
            "error": "range_not_satisfiable",
            "detail": "Empty range.",
        })

    if not start_s:
        # Suffix range: "bytes=-500" means last 500 bytes
        length = int(end_s)
        if length <= 0:
            raise HTTPException(status_code=416, detail={
                "error": "range_not_satisfiable",
                "detail": "Suffix length must be positive.",
            })
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
        if start >= size:
            raise HTTPException(
                status_code=416,
                detail={"error": "range_not_satisfiable", "detail": f"Range start {start} >= size {size}."},
            )
        if end >= size:
            end = size - 1
        if start > end:
            raise HTTPException(status_code=416, detail={
                "error": "range_not_satisfiable",
                "detail": "Range start > end.",
            })
    return start, end


async def _iter_chunks(
    storage: StorageService, key: str, start: int, end: int, chunk_size: int
) -> AsyncIterator[bytes]:
    total = end - start + 1
    sent = 0
    try:
        async for chunk in storage.open_stream(key, start=start, end=end):
            sent += len(chunk)
            yield chunk
    finally:
        # We rely on the route to call active_streams.dec() in a finally
        stream_bytes_total.labels(endpoint="stream").inc(sent)


async def _invalidate_upstream(provider: MediaProvider, media_id: str) -> None:
    """Best-effort: drop a failed upstream URL from the provider cache.

    A resolved CDN URL can rarely go stale before its TTL
    (revoked, IP-bound). Dropping it lets the next request
    re-resolve instead of replaying the bad URL.
    """
    invalidate = getattr(provider, "invalidate_stream", None)
    if not callable(invalidate):
        return
    try:
        await invalidate(media_id)
    except Exception:
        logger.debug("stream_invalidate_failed", extra={"media_id": media_id})


@router.get("/stream/{media_id}")
async def stream_get(
    request: Request,
    media_id: str,
    range_header: Optional[str] = Header(default=None, alias="Range"),
    audio_format: Optional[str] = Query(
        None, alias="format",
        description="m4a: progressive MP4 remux; mp3: transcode — "
                    "universally inline-playable formats"),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    storage: StorageService = Depends(get_storage),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
) -> StreamingResponse:
    return await _do_stream(
        request=request,
        media_id=media_id,
        range_header=range_header,
        fmt=audio_format,
        api_key=api_key,
        session=session,
        rate_limiter=rate_limiter,
        storage=storage,
        stream_proxy=stream_proxy,
        provider=provider,
        method="GET",
    )


@router.head("/stream/{media_id}")
async def stream_head(
    request: Request,
    media_id: str,
    range_header: Optional[str] = Header(default=None, alias="Range"),
    audio_format: Optional[str] = Query(
        None, alias="format",
        description="m4a: progressive MP4 remux; mp3: transcode — "
                    "universally inline-playable formats"),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    storage: StorageService = Depends(get_storage),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
) -> StreamingResponse:
    """HEAD: same headers as GET but no body. Many clients use HEAD to probe
    Range support and file size before issuing a GET."""
    return await _do_stream(
        request=request,
        media_id=media_id,
        range_header=range_header,
        fmt=audio_format,
        api_key=api_key,
        session=session,
        rate_limiter=rate_limiter,
        storage=storage,
        stream_proxy=stream_proxy,
        provider=provider,
        method="HEAD",
    )


async def _do_stream(
    request: Request,
    media_id: str,
    range_header: Optional[str],
    fmt: Optional[str],
    api_key: APIKey,
    session: AsyncSession,
    rate_limiter: RateLimiter,
    storage: StorageService,
    stream_proxy: StreamProxy,
    provider: MediaProvider,
    method: str,
) -> StreamingResponse:
    started = time.perf_counter()
    settings = get_settings()

    # ── 1. Rate limits ────────────────────────────────────────────────────
    rl = await rate_limiter.check(api_key.id, api_key.rate_per_minute, api_key.daily_limit)
    if not rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "detail": rl.reason},
            headers={
                "Retry-After": str(rl.retry_after_seconds),
                "X-RateLimit-Remaining-Minute": str(max(0, rl.remaining_minute)),
                "X-RateLimit-Remaining-Day": str(max(0, rl.remaining_day)),
            },
        )

    # ── 2. Provider → resolve to a stream source ──────────────────────────
    relayed = False
    try:
        src = await provider.get_stream(media_id)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": f"No media with id {media_id!r}.",
        })
    except ProviderUnavailableError as e:
        src = await relay_source(provider, media_id, "audio")
        if src is None:
            raise HTTPException(status_code=503, detail={
                "error": "provider_unavailable",
                "detail": str(e),
            })
        relayed = True
    except ProviderError as e:
        raise HTTPException(status_code=502, detail={
            "error": "provider_error",
            "detail": str(e),
        })

    # ── 3. Resolve size + decide storage vs proxy path ───────────────────
    # A non-empty direct_url means the provider has a remote URL we must
    # proxy; otherwise the bytes are in the local/S3 storage backend.
    if src.direct_url and fmt and fmt.lower() in FIX_FORMATS:
        fixed = await ensure_fixed_source(storage, media_id, src, fmt.lower())
        if fixed is not None:
            src = fixed

    if src.direct_url:
        try:
            head = await stream_proxy.head(src.direct_url)
        except ProviderUnavailableError as e:
            if not relayed:
                # Resolved googlevideo URL is dead (expired at best, our
                # IP flagged at worst): drop the cached entry and try an
                # out-of-band relay before failing.
                await _invalidate_upstream(provider, media_id)
                src = await relay_source(provider, media_id, "audio")
                if src is not None and src.direct_url:
                    relayed = True
                    try:
                        head = await stream_proxy.head(src.direct_url)
                    except ProviderUnavailableError as e2:
                        raise HTTPException(status_code=502, detail={
                            "error": "upstream_unavailable",
                            "detail": str(e2),
                        })
                else:
                    raise HTTPException(status_code=502, detail={
                        "error": "upstream_unavailable",
                        "detail": str(e),
                    })
            else:
                raise HTTPException(status_code=502, detail={
                    "error": "upstream_unavailable",
                    "detail": str(e),
                })
        size = head.size_bytes
        mime_type = head.content_type or src.mime_type
        stream_kind = "proxy"
        stream_target = src.direct_url
    else:
        if not await storage.exists(src.storage_key):
            raise HTTPException(status_code=404, detail={
                "error": "media_not_found",
                "detail": "Audio bytes are not present in storage.",
            })
        size = await storage.size(src.storage_key)
        mime_type = src.mime_type
        stream_kind = "storage"
        stream_target = src.storage_key

    # ── 4. Concurrent stream slot ────────────────────────────────────────
    token = await rate_limiter.acquire_stream(api_key.id, api_key.concurrent_streams_limit)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "too_many_concurrent_streams",
                    "detail": f"Limit: {api_key.concurrent_streams_limit}."},
        )

    slot_released = False

    async def release_slot() -> None:
        """Give the concurrent stream slot back exactly once."""
        nonlocal slot_released
        if slot_released:
            return
        slot_released = True
        await rate_limiter.release_stream(api_key.id, token)

    try:
        # ── 5. Range parsing ─────────────────────────────────────────────
        # An upstream that reports no length has an unknown size: the body is
        # streamed to its end and the answer is sent chunked. A range cannot
        # be served for such an upstream.
        known_size = size > 0
        start = 0
        end = size - 1 if known_size else None
        status_code, content_range = 200, None
        if range_header:
            if not known_size:
                raise HTTPException(status_code=416, detail={
                    "error": "range_not_satisfiable",
                    "detail": "The upstream reports no length, ranges are not supported.",
                })
            parsed = _parse_range(range_header, size)
            if parsed is not None:
                start, end = parsed
                status_code = 206
                content_range = f"bytes {start}-{end}/{size}"
        content_length = end - start + 1 if end is not None else None

        # ── 6. Bookkeeping ───────────────────────────────────────────────
        touch(api_key)
        api_key.total_requests += 1
        try:
            await session.commit()
        except Exception:
            await session.rollback()

        active_streams.inc()
        api_request_duration_seconds.labels(endpoint="stream", method=method).observe(
            time.perf_counter() - started
        )

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": mime_type,
            "Content-Disposition": f'inline; filename="audio.{_ext_for(mime_type)}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        }
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if content_range:
            headers["Content-Range"] = content_range

        chunk_size = settings.stream_chunk_size
        if method == "HEAD":
            # No body for HEAD. Release the slot now.
            await release_slot()
            active_streams.dec()
            return StreamingResponse(
                iter(()),
                status_code=status_code,
                headers=headers,
                media_type=mime_type,
            )

        async def body() -> AsyncIterator[bytes]:
            sent = 0
            try:
                if stream_kind == "proxy":
                    workers = settings.stream_parallel_workers
                    if workers > 1 and end is not None:
                        stream_iter = stream_proxy.stream_parallel(
                            stream_target, start=start, end=end,
                            chunk_size=chunk_size, workers=workers,
                        )
                    else:
                        stream_iter = stream_proxy.stream(
                            stream_target, start=start, end=end,
                            chunk_size=chunk_size,
                        )
                    async for chunk in stream_iter:
                        sent += len(chunk)
                        yield chunk
                else:
                    async for chunk in storage.open_stream(
                        stream_target, start=start, end=end
                    ):
                        sent += len(chunk)
                        yield chunk
            except ProviderUnavailableError:
                await _invalidate_upstream(provider, media_id)
                raise
            finally:
                stream_bytes_total.labels(endpoint="stream").inc(sent)
                active_streams.dec()
                await release_slot()
            # Best-effort: update bytes_streamed counter
            api_key.bytes_streamed += sent
            try:
                await session.commit()
            except Exception:
                await session.rollback()
            logger.info("stream_complete", extra={
                "key_id": api_key.id,
                "media_id": media_id,
                "bytes": sent,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": status_code,
                "source": stream_kind,
            })

        return StreamingResponse(
            body(),
            status_code=status_code,
            headers=headers,
            media_type=mime_type,
        )
    except BaseException:
        # Everything that fails before the response is built has to give the
        # concurrent stream slot back, otherwise the slot leaks until the
        # process restarts.
        await release_slot()
        raise
