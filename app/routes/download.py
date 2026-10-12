"""Download endpoint: fetch media as a file attachment.

GET  /download/{media_id}?kind=audio|video
HEAD /download/{media_id}?kind=audio|video

Same resolution path as /stream (provider -> storage or proxied
direct URL), but the response carries ``Content-Disposition:
attachment`` so clients save the bytes as a file instead of
playing them inline.

``kind`` selects the representation: ``audio`` (default) or
``video``. Providers that only expose one representation ignore
the parameter and serve what they have.

Authentication: requires a valid API key (query or header).
Rate limiting: per-minute + daily + concurrent stream slots.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import re
import tempfile
import time
from typing import AsyncIterator, Optional, Tuple
from urllib.parse import quote

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
from app.services import mirror_store
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
    StreamSource,
)
from app.services.storage import StorageService
from app.services.stream_fallback import relay_source
from app.services.stream_proxy import StreamProxy
from app.utils.logging import get_logger
from app.utils.metrics import (
    active_streams,
    api_request_duration_seconds,
    stream_bytes_total,
)
from app.utils.rate_limit import RateLimiter

from app.routes.stream import _parse_range

logger = get_logger(__name__)
router = APIRouter()

_KINDS = ("audio", "video")

# extensions we recognise on a media id / storage key
_KNOWN_EXTS = {
    "mp3", "m4a", "aac", "webm", "ogg", "flac", "wav", "wma",
    "mp4", "mov", "avi", "mkv",
}

# mime type -> file extension for the download filename
_EXT_BY_MIME = {
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/wav": "wav",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
}


def _extension_for(mime_type: str, media_id: str) -> str:
    # Prefer an explicit media extension (storage-backed files
    # carry their real format in the key); YouTube ids have none.
    if "." in media_id:
        tail = media_id.rsplit(".", 1)[-1].lower()
        if tail in _KNOWN_EXTS:
            return tail
    base = (mime_type or "").split(";")[0].strip().lower()
    if base in _EXT_BY_MIME:
        return _EXT_BY_MIME[base]
    if "." in media_id:
        tail = media_id.rsplit(".", 1)[-1].lower()
        if tail and len(tail) <= 8 and all(c.isalnum() for c in tail):
            return tail
    return "bin"


def _safe_filename(title: str, media_id: str) -> str:
    cleaned = re.sub(r"[^\w\s.-]+", "_", title or "")
    cleaned = re.sub(r"\s+", "_", cleaned).strip(". ")[:120]
    return cleaned or media_id[:120]


def _content_disposition(filename: str) -> str:
    safe = filename.replace('"', "'").replace("\r", "").replace("\n", "")
    ascii_fallback = re.sub(r"[^\x20-\x7e]|;", "_", safe) or "download"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


async def _fetch_url_to_temp(
    stream_proxy: StreamProxy,
    url: str,
    workers: int,
    chunk_size: int = 65536,
) -> str:
    """Fetch ``url`` to a local temp file, splitting the
    download across several concurrent Range requests.

    A single CDN connection is often throttled to a few
    hundred KB/s; the same parallel technique the stream
    endpoint uses lifts aggregate throughput to several
    MB/s. The caller deletes the file."""
    head = await stream_proxy.head(url)
    size = head.size_bytes
    fd, path = tempfile.mkstemp()
    os.close(fd)
    loop = asyncio.get_running_loop()
    try:
        with open(path, "wb") as handle:
            if head.supports_range:
                stream_iter = stream_proxy.stream_parallel(
                    url, start=0, end=size - 1,
                    chunk_size=chunk_size, workers=workers,
                )
            else:
                stream_iter = stream_proxy.stream(
                    url, start=0, end=size - 1,
                    chunk_size=chunk_size,
                )
            buffer = bytearray()
            async for chunk in stream_iter:
                buffer.extend(chunk)
                if len(buffer) >= 1024 * 1024:
                    await loop.run_in_executor(None, handle.write, bytes(buffer))
                    buffer.clear()
            if buffer:
                await loop.run_in_executor(None, handle.write, bytes(buffer))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise
    return path


async def _merge_dash_to_temp(
    stream_proxy: StreamProxy,
    video_url: str,
    audio_url: str,
    workers: int,
) -> str:
    """Fetch the two DASH streams to local temp files with
    parallel Range requests, then remux them into a temp
    MP4 via ffmpeg (stream copy — no re-encode) and return
    the merged path. Fetching through the parallel proxy is
    far faster than letting ffmpeg open single connections
    to a throttled CDN. The caller deletes the merged file;
    the intermediates are removed here."""
    video_tmp: Optional[str] = None
    audio_tmp: Optional[str] = None
    try:
        video_tmp = await _fetch_url_to_temp(stream_proxy, video_url, workers)
        audio_tmp = await _fetch_url_to_temp(stream_proxy, audio_url, workers)
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_tmp,
            "-i", audio_tmp,
            "-c", "copy",
            "-movflags", "faststart",
            path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await proc.communicate()
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill()
            with contextlib.suppress(OSError):
                os.unlink(path)
            raise ProviderUnavailableError("ffmpeg merge interrupted")
        if proc.returncode != 0:
            with contextlib.suppress(OSError):
                os.unlink(path)
            tail = stderr.decode(errors="ignore")[-800:]
            raise ProviderUnavailableError(f"ffmpeg merge failed: {tail}")
        return path
    finally:
        for tmp in (video_tmp, audio_tmp):
            if tmp:
                with contextlib.suppress(OSError):
                    os.unlink(tmp)


async def _temp_file_stream(
    path: str, start: int, end: int, chunk_size: int = 65536
) -> AsyncIterator[bytes]:
    """Yield bytes ``[start, end]`` from a local file, doing
    the blocking reads in a worker thread so the event loop
    is never blocked. Reads in ~1 MB chunks to keep executor
    round-trips bounded even for large video files."""
    loop = asyncio.get_running_loop()
    read_size = max(chunk_size, 1024 * 1024)
    with open(path, "rb") as handle:
        await loop.run_in_executor(None, handle.seek, start)
        remaining = end - start + 1
        while remaining > 0:
            n = min(read_size, remaining)
            chunk = await loop.run_in_executor(None, handle.read, n)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


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


async def _title_for(provider: MediaProvider, media_id: str) -> str:
    """Best-effort metadata lookup for a friendly filename."""
    try:
        meta = await provider.get_info(media_id)
        return meta.title or media_id
    except Exception:
        return media_id


async def _metadata_for(
    provider: MediaProvider, media_id: str
) -> Tuple[str, str]:
    """Best-effort metadata lookup for ID3 tags:
    returns ``(title, artist)``."""
    try:
        meta = await provider.get_info(media_id)
        return meta.title or media_id, meta.artist or ""
    except Exception:
        return media_id, ""


async def _serve_mp3(
    provider: MediaProvider,
    media_id: str,
    api_key: APIKey,
    rate_limiter: RateLimiter,
    session: AsyncSession,
    src: StreamSource,
    method: str,
    started: float,
):
    """Download-only MP3: transcode the upstream audio
    to MP3 on the fly with ID3 title/artist tags and
    stream it straight from ffmpeg. No bytes are written
    to disk or cached. Because the output size is only
    known after a full transcode, the response is chunked
    (no Content-Length) and Range is not supported; m4a
    stays the seekable representation for /stream/."""
    settings = get_settings()
    title, artist = await _metadata_for(provider, media_id)
    filename = f"{_safe_filename(title, media_id)}.mp3"

    touch(api_key)
    api_key.total_requests += 1
    try:
        await session.commit()
    except Exception:
        await session.rollback()
    api_request_duration_seconds.labels(endpoint="download", method=method).observe(
        time.perf_counter() - started
    )

    headers = {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": _content_disposition(filename),
    }
    if method == "HEAD":
        # A HEAD cannot know the size without a full
        # transcode, so it reports the content type only.
        return StreamingResponse(
            iter(()), status_code=200, headers=headers, media_type="audio/mpeg",
        )

    token = await rate_limiter.acquire_stream(
        api_key.id, api_key.concurrent_streams_limit
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "too_many_concurrent_streams",
                    "detail": f"Limit: {api_key.concurrent_streams_limit}."},
        )
    active_streams.inc()

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src.direct_url,
        "-c:a", "libmp3lame", "-q:a", "2",
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
        "-f", "mp3", "pipe:1",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # Buffer the first chunk so an immediate upstream or
    # ffmpeg failure surfaces as a 502 rather than an
    # empty 200 body.
    try:
        first = await asyncio.wait_for(
            proc.stdout.read(settings.stream_chunk_size), timeout=30.0
        )
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        await proc.wait()
        await rate_limiter.release_stream(api_key.id, token)
        active_streams.dec()
        raise HTTPException(status_code=504, detail={
            "error": "upstream_timeout",
            "detail": "ffmpeg mp3 transcode timed out.",
        })
    if not first:
        _, stderr = await proc.communicate()
        await rate_limiter.release_stream(api_key.id, token)
        active_streams.dec()
        raise HTTPException(status_code=502, detail={
            "error": "upstream_unavailable",
            "detail": f"ffmpeg mp3 transcode failed: {stderr.decode(errors='ignore')[-400:]}",
        })

    async def mp3_body() -> AsyncIterator[bytes]:
        sent = len(first)
        try:
            yield first
            while True:
                chunk = await proc.stdout.read(settings.stream_chunk_size)
                if not chunk:
                    break
                sent += len(chunk)
                yield chunk
            await proc.wait()
        finally:
            if proc.returncode is None:
                with contextlib.suppress(Exception):
                    proc.kill()
            stream_bytes_total.labels(endpoint="download").inc(sent)
            active_streams.dec()
            await rate_limiter.release_stream(api_key.id, token)
            api_key.bytes_streamed += sent
            try:
                await session.commit()
            except Exception:
                await session.rollback()
            logger.info("download_complete", extra={
                "key_id": api_key.id,
                "media_id": media_id,
                "kind": "audio",
                "bytes": sent,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": 200,
                "source": "mp3_transcode",
            })

    return StreamingResponse(
        mp3_body(), status_code=200, headers=headers, media_type="audio/mpeg",
    )


@router.get("/download/{media_id}")
async def download_get(
    request: Request,
    media_id: str,
    kind: str = Query("audio", description="audio or video"),
    fmt: Optional[str] = Query(default=None, alias="format", description="original or mp3"),
    max_height: Optional[int] = Query(
        default=None, ge=1, le=4320,
        description="cap video resolution height (e.g. 1080) for DASH video",
    ),
    range_header: Optional[str] = Header(default=None, alias="Range"),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    storage: StorageService = Depends(get_storage),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
) -> StreamingResponse:
    return await _do_download(
        request=request,
        media_id=media_id,
        kind=kind,
        format_param=fmt,
        max_height=max_height,
        range_header=range_header,
        api_key=api_key,
        session=session,
        rate_limiter=rate_limiter,
        storage=storage,
        stream_proxy=stream_proxy,
        provider=provider,
        method="GET",
    )


@router.head("/download/{media_id}")
async def download_head(
    request: Request,
    media_id: str,
    kind: str = Query("audio", description="audio or video"),
    fmt: Optional[str] = Query(default=None, alias="format", description="original or mp3"),
    max_height: Optional[int] = Query(
        default=None, ge=1, le=4320,
        description="cap video resolution height (e.g. 1080) for DASH video",
    ),
    range_header: Optional[str] = Header(default=None, alias="Range"),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    storage: StorageService = Depends(get_storage),
    stream_proxy: StreamProxy = Depends(get_stream_proxy),
    provider: MediaProvider = Depends(get_provider),
) -> StreamingResponse:
    """HEAD: same headers as GET but no body. Clients probe size and
    Range support before issuing a full download."""
    return await _do_download(
        request=request,
        media_id=media_id,
        kind=kind,
        format_param=fmt,
        max_height=max_height,
        range_header=range_header,
        api_key=api_key,
        session=session,
        rate_limiter=rate_limiter,
        storage=storage,
        stream_proxy=stream_proxy,
        provider=provider,
        method="HEAD",
    )


async def _do_download(
    request: Request,
    media_id: str,
    kind: str,
    format_param: Optional[str],
    max_height: Optional[int],
    range_header: Optional[str],
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

    # ── 0. Representation selection ─────────────────────────────────
    if kind not in _KINDS:
        raise HTTPException(status_code=400, detail={
            "error": "invalid_kind",
            "detail": f"kind must be one of {list(_KINDS)}.",
        })

    # ── 1. Rate limits ──────────────────────────────────────────────
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

    # ── 2. Provider → resolve a stream source for the requested kind
    # (a mirror copy, when one exists and the provider is down, is
    # reached through relay_source's tier chain — the live provider is
    # always faster than the mirror host and is tried first.)
    try:
        src = await provider.get_stream_by_type(
            media_id, kind, prefer_dash=(kind == "video"), max_height=max_height
        )
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": f"No media with id {media_id!r}.",
        })
    except ProviderUnavailableError as e:
        src = await relay_source(provider, media_id, kind)
        if src is None:
            raise HTTPException(status_code=503, detail={
                "error": "provider_unavailable",
                "detail": str(e),
            })
    except ProviderError as e:
        raise HTTPException(status_code=502, detail={
            "error": "provider_error",
            "detail": str(e),
        })

    # ── 2b. MP3 transcode (download-only, on-the-fly) ──────
    if format_param == "mp3" and kind == "audio" and src.direct_url:
        return await _serve_mp3(
            provider=provider, media_id=media_id, api_key=api_key,
            rate_limiter=rate_limiter, session=session,
            src=src, method=method, started=started,
        )

    # ── 3. Resolve size + decide storage vs proxy vs dash path ──────
    dash_tmp_path: Optional[str] = None
    if src.is_dash and src.direct_url and src.direct_url_audio:
        # High-quality video: two DASH streams that must be
        # remuxed together. For GET we merge them into a temp
        # file with ffmpeg and serve it Range-capable; for HEAD
        # we approximate the size as the sum of the two streams
        # so a probe never triggers a full merge.
        mime_type = "video/mp4"
        if method == "HEAD":
            try:
                vhead = await stream_proxy.head(src.direct_url)
                ahead = await stream_proxy.head(src.direct_url_audio)
            except ProviderUnavailableError as e:
                await _invalidate_upstream(provider, media_id)
                raise HTTPException(status_code=502, detail={
                    "error": "upstream_unavailable",
                    "detail": str(e),
                })
            size = vhead.size_bytes + ahead.size_bytes
            stream_kind = "dash_head"
            stream_target = ""
        else:
            try:
                dash_tmp_path = await _merge_dash_to_temp(
                    stream_proxy, src.direct_url, src.direct_url_audio,
                    settings.stream_parallel_workers,
                )
            except ProviderUnavailableError as e:
                await _invalidate_upstream(provider, media_id)
                raise HTTPException(status_code=502, detail={
                    "error": "upstream_unavailable",
                    "detail": str(e),
                })
            size = os.path.getsize(dash_tmp_path)
            stream_kind = "dash_temp"
            stream_target = dash_tmp_path
    elif src.direct_url:
        try:
            head = await stream_proxy.head(src.direct_url)
        except ProviderUnavailableError as e:
            await _invalidate_upstream(provider, media_id)
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
                "detail": "Media bytes are not present in storage.",
            })
        size = await storage.size(src.storage_key)
        mime_type = src.mime_type
        stream_kind = "storage"
        stream_target = src.storage_key

    # ── 4. Concurrent stream slot ───────────────────────────────────
    token = await rate_limiter.acquire_stream(api_key.id, api_key.concurrent_streams_limit)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "too_many_concurrent_streams",
                    "detail": f"Limit: {api_key.concurrent_streams_limit}."},
        )

    # ── 5. Range parsing ────────────────────────────────────────────
    start, end, status_code, content_range = 0, size - 1, 200, None
    if range_header:
        parsed = _parse_range(range_header, size)
        if parsed is not None:
            start, end = parsed
            status_code = 206
            content_range = f"bytes {start}-{end}/{size}"
    content_length = end - start + 1

    # ── 6. Filename from metadata (best effort) ─────────────────────
    title = await _title_for(provider, media_id)
    filename = f"{_safe_filename(title, media_id)}.{_extension_for(mime_type, media_id)}"

    # ── 7. Bookkeeping ──────────────────────────────────────────────
    touch(api_key)
    api_key.total_requests += 1
    try:
        await session.commit()
    except Exception:
        await session.rollback()

    active_streams.inc()
    api_request_duration_seconds.labels(endpoint="download", method=method).observe(
        time.perf_counter() - started
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": _content_disposition(filename),
    }
    if content_range:
        headers["Content-Range"] = content_range

    chunk_size = settings.stream_chunk_size
    if method == "HEAD":
        # No body for HEAD. Release the slot now.
        await rate_limiter.release_stream(api_key.id, token)
        active_streams.dec()
        return StreamingResponse(
            iter(()),
            status_code=status_code,
            headers=headers,
            media_type=mime_type,
        )

    async def body() -> AsyncIterator[bytes]:
        sent = 0
        is_mirror = src.storage_key.startswith("mirror/")
        # Captured copy of a *complete* proxy delivery, so the exact
        # bytes the client received can be mirrored for later hits.
        mirrorable = (
            not is_mirror
            and stream_kind == "proxy"
            and status_code == 200
            and not src.storage_key.startswith(("cached/", "mirror/"))
        )
        tee = bytearray() if mirrorable else None
        completed = False
        try:
            if stream_kind == "dash_temp":
                async for chunk in _temp_file_stream(
                    stream_target, start, end, chunk_size
                ):
                    sent += len(chunk)
                    yield chunk
            elif stream_kind == "proxy":
                workers = settings.stream_parallel_workers
                if workers > 1:
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
                    if tee is not None:
                        tee.extend(chunk)
                    yield chunk
            else:
                async for chunk in storage.open_stream(
                    stream_target, start=start, end=end
                ):
                    sent += len(chunk)
                    yield chunk
            completed = True
        except ProviderUnavailableError:
            if is_mirror:
                mirror_store.invalidate(media_id)
            await _invalidate_upstream(provider, media_id)
            raise
        finally:
            if (
                completed
                and tee is not None
                and len(tee) == content_length
                and len(tee) <= mirror_store.MAX_MIRROR_BYTES
            ):
                mirror_store.enqueue_mirror(media_id, kind, mime_type, bytes(tee))
            stream_bytes_total.labels(endpoint="download").inc(sent)
            active_streams.dec()
            await rate_limiter.release_stream(api_key.id, token)
            api_key.bytes_streamed += sent
            try:
                await session.commit()
            except Exception:
                await session.rollback()
            # DASH video is merged into a temp file; remove it
            # now that the response has been fully streamed.
            if dash_tmp_path:
                with contextlib.suppress(OSError):
                    os.unlink(dash_tmp_path)
            logger.info("download_complete", extra={
                "key_id": api_key.id,
                "media_id": media_id,
                "kind": kind,
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
