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
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, Optional, Tuple
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
from app.services.audio_fix import clamp_mp3_bitrate, ensure_fixed_source
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
from app.utils.ffmpeg import ffmpeg_binary
from app.utils.logging import get_logger
from app.utils.metrics import (
    active_streams,
    api_request_duration_seconds,
    stream_bytes_total,
)
from app.utils.rate_limit import RateLimiter
from app.utils.telemetry import telemetry, provider_of

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
    chunk_size: int = 262144,
) -> str:
    """Fetch ``url`` to a local temp file via the cookie-bearing
    parallel Range proxy. The caller deletes the file."""
    return await stream_proxy.fetch_to_temp(
        url, workers=workers, chunk_size=chunk_size,
    )


# ── Single-flight merge ───────────────────────────────────────────
# A DASH/HLS merge fetches both streams and runs ffmpeg over them.
# A client that downloads in parallel sends one request per chunk, and
# every one of them would start its own merge: six merges for one file
# starve the box and the client sees no bytes for minutes. One merge
# per cache key is enough, the other requests wait for it and then
# serve the cached file.
_merge_flights: dict[str, asyncio.Task] = {}
_merge_flight_guard = asyncio.Lock()


async def _single_flight(key: str, factory: Callable[[], Awaitable[str]]) -> str:
    """Run one merge per key; parallel requests share its result."""
    async with _merge_flight_guard:
        task = _merge_flights.get(key)
        if task is None:
            task = asyncio.ensure_future(factory())
            _merge_flights[key] = task
    try:
        # shield: a cancelled caller must not kill the shared merge,
        # the other callers still need the file.
        return await asyncio.shield(task)
    finally:
        if task.done():
            async with _merge_flight_guard:
                if _merge_flights.get(key) is task:
                    _merge_flights.pop(key, None)


def _guard_merged_size(settings, path: str, size: int) -> None:
    """Refuse a merged video that is bigger than the limit.

    The size of an HLS remux is unknown before it ran, so the check
    happens after it. The file is removed, a chat cannot take it.
    """
    limit = int(getattr(settings, "video_max_bytes", 0) or 0)
    if limit <= 0 or size <= limit:
        return
    with contextlib.suppress(OSError):
        os.unlink(path)
    raise HTTPException(status_code=413, detail={
        "error": "video_too_large",
        "detail": (
            f"the video is {size} bytes, the limit is {limit}. "
            "Ask for a lower resolution."
        ),
    })


async def _guard_video_size(
    settings,
    src: StreamSource,
    stream_proxy: StreamProxy,
    provider: MediaProvider,
    media_id: str,
) -> None:
    """Refuse a video that is bigger than the limit.

    The size of the two DASH streams is known before they are fetched,
    so a video that no chat can take is refused in a moment instead of
    after a multi-minute merge of gigabytes.
    """
    limit = int(getattr(settings, "video_max_bytes", 0) or 0)
    if limit <= 0:
        return
    try:
        video_head = await stream_proxy.head(src.direct_url)
        audio_head = await stream_proxy.head(src.direct_url_audio)
    except ProviderUnavailableError:
        # The size stays unknown, the merge itself is bounded by the
        # file limit check after it ran.
        return
    total = video_head.size_bytes + audio_head.size_bytes
    if total <= limit:
        return
    await _invalidate_upstream(provider, media_id)
    raise HTTPException(status_code=413, detail={
        "error": "video_too_large",
        "detail": (
            f"the video is {total} bytes, the limit is {limit}. "
            "Ask for a lower resolution."
        ),
    })


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
        # Both streams are fetched at the same time: the audio stream is
        # small, but it used to wait for the whole video download.
        video_tmp, audio_tmp = await asyncio.gather(
            _fetch_url_to_temp(stream_proxy, video_url, workers),
            _fetch_url_to_temp(stream_proxy, audio_url, workers),
        )
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        cmd = [
            ffmpeg_binary(), "-y", "-hide_banner", "-loglevel", "error",
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


def _url_is_manifest(url: Optional[str]) -> bool:
    """True when a resolved URL is a playlist, not media bytes."""
    if not url:
        return False
    low = url.lower()
    return ".m3u8" in low or ".mpd" in low or "manifest" in low


async def _merge_hls_to_temp(
    video_url: str,
    audio_url: Optional[str],
) -> str:
    """Remux an HLS variant playlist into a local MP4 with ffmpeg.

    A playlist is metadata, not media: only ffmpeg can fetch its
    segments and write the actual video bytes. When a separate
    audio track exists it is muxed in as a second input; ffmpeg
    copies both streams (no re-encode) so the remux stays fast.
    Returns the merged path; the caller deletes it.

    HLS remuxes are bounded but slow (a 4K song can take minutes),
    so the subprocess gets a generous timeout and its stderr is
    surfaced on failure instead of a bare 502."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    cmd = [
        ffmpeg_binary(), "-y", "-hide_banner", "-loglevel", "error",
        "-timeout", "600000000",
        "-i", video_url,
    ]
    if audio_url:
        cmd += ["-i", audio_url]
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?"]
    cmd += ["-c", "copy", "-movflags", "faststart", path]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise ProviderUnavailableError("ffmpeg hls remux timed out")
    if proc.returncode != 0:
        with contextlib.suppress(OSError):
            os.unlink(path)
        tail = stderr.decode(errors="ignore")[-800:]
        raise ProviderUnavailableError(f"ffmpeg hls remux failed: {tail}")
    return path


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


# ── Merged DASH video cache ──────────────────────────────────────
# A DASH merge costs 100-500 MB of upstream fetching per request;
# without a cache, one slow client download makes voice-chat bots
# retry the identical merge in a loop. Cache results on disk keyed
# by media id + height cap and serve repeats instantly.

def _merge_cache_path(settings, media_id: str, max_height: Optional[int]) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.:-]", "_", media_id)
    height = (max_height or settings.video_max_height_cap) // 72 * 72
    return Path(settings.video_merge_cache_dir) / f"{safe}.{height}.mp4"


def _cached_merge_file(
    settings, media_id: str, max_height: Optional[int], kind: str
) -> Optional[Path]:
    """The merged video of a media id, when it is already on disk.

    Only a video download can use it, and only the ids of the provider
    that produces DASH/HLS merges (YouTube) carry such a file.
    """
    if kind != "video" or not media_id.startswith("yt:"):
        return None
    path = _merge_cache_path(settings, media_id, max_height)
    try:
        if path.is_file() and path.stat().st_size > 100_000:
            return path
    except OSError:
        return None
    return None


def _stash_merge_cache(settings, cache_path: Path, merged_tmp: str) -> None:
    """Move a freshly merged temp file into the cache (best effort).

    Skips if another request already cached the same key, in that case the
    freshly merged copy is dropped so it does not stay on the disk. The cache
    can live on another filesystem than the temp file, then the file is copied
    instead of renamed."""
    tmp_stash = str(cache_path) + f".part{os.getpid()}.{time.time_ns()}"
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            with contextlib.suppress(OSError):
                os.unlink(merged_tmp)
            return
        try:
            os.replace(merged_tmp, tmp_stash)
        except OSError:
            # Different filesystems cannot be renamed into each other.
            shutil.move(merged_tmp, tmp_stash)
        os.replace(tmp_stash, cache_path)
        _trim_merge_cache(settings)
    except OSError:
        with contextlib.suppress(OSError):
            Path(tmp_stash).unlink(missing_ok=True)


def _trim_merge_cache(settings) -> None:
    """Keep the merge cache dir under its byte budget, deleting
    oldest files first but never files younger than the live-serve
    window (a response may still be streaming from one)."""
    cache_dir = Path(settings.video_merge_cache_dir)
    budget = max(64, settings.video_merge_cache_max_mb) * 1024 * 1024
    try:
        entries = [p for p in cache_dir.glob("*.mp4") if p.is_file()]
        sized = [(p.stat().st_mtime, p.stat().st_size, p) for p in entries]
    except OSError:
        return
    total = sum(sz for _, sz, _ in sized)
    if total <= budget:
        return
    fresh = time.time() - 900
    # Oldest first: a file that was just merged is the one a client is
    # waiting for, the stale ones are the ones nobody asks for again.
    for _, sz, p in sorted(sized):
        if total <= budget:
            break
        try:
            if p.stat().st_mtime >= fresh:
                continue
        except OSError:
            continue
        try:
            p.unlink()
            with contextlib.suppress(OSError):
                p.with_suffix(".json").unlink()
            total -= sz
        except OSError:
            break


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


def _merge_cache_title(path: Path) -> str:
    """The title of a merged video, when it was stored beside it.

    The metadata of a video costs an extraction of seconds, so the
    title of a merged file is written next to it. A cached video is
    then served without asking the provider at all.
    """
    try:
        raw = path.with_suffix(".json").read_text(errors="ignore")
        data = json.loads(raw)
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("title") or "")


def _store_merge_cache_title(path: Path, title: str) -> None:
    """Write the title of a merged video next to the file."""
    if not title:
        return
    try:
        path.with_suffix(".json").write_text(
            json.dumps({"title": title}), encoding="utf-8"
        )
    except OSError:
        pass


async def _serve_mp3(
    provider: MediaProvider,
    media_id: str,
    api_key: APIKey,
    rate_limiter: RateLimiter,
    session: AsyncSession,
    storage: StorageService,
    stream_proxy: StreamProxy,
    src: StreamSource,
    method: str,
    started: float,
    range_header: Optional[str],
    bitrate: Optional[int],
):
    """MP3 download: transcode (CBR, default 192 kbps) into storage,
    then serve Range-capable from the cached file. Repeat hits skip
    ffmpeg entirely. ID3 title/artist tags are written on first build."""
    settings = get_settings()
    kbps = clamp_mp3_bitrate(bitrate)
    title, artist = await _metadata_for(provider, media_id)
    filename = f"{_safe_filename(title, media_id)}.mp3"

    fixed = await ensure_fixed_source(
        storage, media_id, src, "mp3",
        bitrate=kbps,
        stream_proxy=stream_proxy,
        workers=settings.stream_parallel_workers,
        title=title,
        artist=artist,
    )
    if fixed is None or not await storage.exists(fixed.storage_key):
        raise HTTPException(status_code=502, detail={
            "error": "upstream_unavailable",
            "detail": "ffmpeg mp3 transcode failed.",
        })
    size = await storage.size(fixed.storage_key)

    touch(api_key)
    api_key.total_requests += 1
    try:
        await session.commit()
    except Exception:
        await session.rollback()
    api_request_duration_seconds.labels(endpoint="download", method=method).observe(
        time.perf_counter() - started
    )

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
        "Content-Type": "audio/mpeg",
        "Content-Length": str(content_length),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": _content_disposition(filename),
        "X-Audio-Bitrate": str(kbps),
    }
    if content_range:
        headers["Content-Range"] = content_range

    if method == "HEAD":
        return StreamingResponse(
            iter(()), status_code=status_code, headers=headers,
            media_type="audio/mpeg",
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

    async def mp3_body() -> AsyncIterator[bytes]:
        sent = 0
        try:
            async for chunk in storage.open_stream(
                fixed.storage_key, start=start, end=end
            ):
                sent += len(chunk)
                yield chunk
        finally:
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
                "status": status_code,
                "source": "mp3_cache",
            })

    return StreamingResponse(
        mp3_body(), status_code=status_code, headers=headers,
        media_type="audio/mpeg",
    )


@router.get("/download/{media_id}")
async def download_get(
    request: Request,
    media_id: str,
    kind: str = Query("audio", description="audio or video"),
    fmt: Optional[str] = Query(default=None, alias="format", description="original or mp3"),
    bitrate: Optional[int] = Query(
        default=None, ge=64, le=320,
        description="MP3 CBR kbps (64-320); only used with format=mp3",
    ),
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
        bitrate=bitrate,
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
    bitrate: Optional[int] = Query(
        default=None, ge=64, le=320,
        description="MP3 CBR kbps (64-320); only used with format=mp3",
    ),
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
        bitrate=bitrate,
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
    bitrate: Optional[int],
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

    # ── 1a. Effective video height (before resolving!) ──────────────
    # Default is the soft cap (720p, sized for voice-chat previews);
    # an explicit request is honoured up to the hard cap (2160p), so a
    # client can opt into 4K. Resolving first and clamping after (the
    # old order) fetched multi-hundred-MB streams only to relabel them.
    effective_height = max_height
    if kind == "video":
        requested = max_height or settings.video_max_height_cap
        hard = max(1, settings.video_max_height_hard_cap)
        effective_height = min(max(1, requested), hard)

    # ── 1b. Merged video on disk ──────────────────────────────────
    # A merged DASH/HLS video is a complete file on disk. When it is
    # there, the client gets it without asking the provider: resolving
    # the stream costs seconds of yt-dlp work and the bytes are ready.
    cached_merge = _cached_merge_file(settings, media_id, effective_height, kind)

    # ── 2. Provider → resolve a stream source for the requested kind
    # (a mirror copy, when one exists and the provider is down, is
    # reached through relay_source's tier chain — the live provider is
    # always faster than the mirror host and is tried first.)
    if cached_merge is not None:
        src = StreamSource(
            storage_key="",
            size_bytes=cached_merge.stat().st_size,
            mime_type="video/mp4",
        )
    else:
        try:
            src = await provider.get_stream_by_type(
                media_id, kind, prefer_dash=(kind == "video"), max_height=effective_height
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

    # ── 2a. Telemetry: a successful download request ─────────────
    # The title is resolved once and reused for the file name. A
    # merged video carries its title beside it, so a cached video is
    # served without an extraction.
    title = _merge_cache_title(cached_merge) if cached_merge is not None else ""
    if not title:
        title = await _title_for(provider, media_id)
    telemetry.record_download(
        media_id,
        title=title,
        provider=provider_of(media_id),
        size_bytes=src.size_bytes or 0,
    )

    # ── 2b. MP3 transcode (download-only, on-the-fly) ──────
    if format_param == "mp3" and kind == "audio" and src.direct_url:
        return await _serve_mp3(
            provider=provider, media_id=media_id, api_key=api_key,
            rate_limiter=rate_limiter, session=session,
            storage=storage, stream_proxy=stream_proxy,
            src=src, method=method, started=started,
            range_header=range_header, bitrate=bitrate,
        )

    # ── 3. Resolve size + decide storage vs proxy vs dash/hls path ──
    dash_tmp_path: Optional[str] = None
    delete_dash_after = False
    merge_cache_path: Optional[Path] = None
    size_known = True
    if cached_merge is not None:
        # The merged video is on disk: no provider call, no merge, the
        # file is served Range-capable right away.
        mime_type = "video/mp4"
        dash_tmp_path = str(cached_merge)
        size = cached_merge.stat().st_size
        stream_kind = "dash_cache"
        stream_target = dash_tmp_path
    elif src.is_dash and src.direct_url and src.direct_url_audio:
        # High-quality video: two progressive DASH streams that must
        # be remuxed together. A prior merge may be cached on disk —
        # serve it directly and skip the multi-minute refetch.
        # Without a cache hit, the merge runs once per media id (the
        # parallel chunk requests of a client share it) and the merged
        # file is served Range-capable.
        # A HEAD never remuxes and never guesses a length: the length
        # of the merged file is unknown until the merge ran, and a
        # wrong Content-Length makes a range client address bytes that
        # do not exist. The HEAD therefore reports no size and no range
        # support, so the client asks for the file with one GET.
        mime_type = "video/mp4"
        merge_cache_path = _merge_cache_path(settings, media_id, effective_height)
        if (
            merge_cache_path.is_file()
            and merge_cache_path.stat().st_size > 100_000
        ):
            dash_tmp_path = str(merge_cache_path)
            size = merge_cache_path.stat().st_size
            stream_kind = "dash_cache"
            stream_target = dash_tmp_path
        elif method == "HEAD":
            stream_kind = "dash_head"
            stream_target = ""
            size = 0
            size_known = False
        else:
            # The size of the two streams is known before the merge: a
            # 4K stream of a long video is several gigabytes, and
            # merging it wastes minutes and disk for a file no chat can
            # take. Such a video is refused before the work starts.
            await _guard_video_size(settings, src, stream_proxy, provider, media_id)

            async def _merge_dash() -> str:
                merged_tmp = await _merge_dash_to_temp(
                    stream_proxy, src.direct_url, src.direct_url_audio,
                    settings.stream_parallel_workers,
                )
                _stash_merge_cache(settings, merge_cache_path, merged_tmp)
                _store_merge_cache_title(merge_cache_path, title)
                if merge_cache_path.is_file() and merge_cache_path.stat().st_size > 0:
                    return str(merge_cache_path)
                return merged_tmp

            try:
                dash_tmp_path = await _single_flight(
                    str(merge_cache_path), _merge_dash
                )
            except ProviderUnavailableError as e:
                await _invalidate_upstream(provider, media_id)
                raise HTTPException(status_code=502, detail={
                    "error": "upstream_unavailable",
                    "detail": str(e),
                })
            if dash_tmp_path == str(merge_cache_path):
                stream_kind = "dash_cache"
            else:
                stream_kind = "dash_temp"
                delete_dash_after = True
            size = os.path.getsize(dash_tmp_path)
            _guard_merged_size(settings, dash_tmp_path, size)
            stream_target = dash_tmp_path
    elif src.is_hls and src.direct_url:
        # Manifest-based video: an m3u8 playlist describes segments
        # but carries no media bytes. Only ffmpeg can assemble it
        # into the seekable MP4 a download client expects. Merged
        # results are disk-cached like DASH merges; a HEAD never
        # triggers the (multi-minute) remux and reports no size
        # because the output length is unknown until it runs.
        mime_type = "video/mp4"
        merge_cache_path = _merge_cache_path(settings, media_id, effective_height)
        if (
            merge_cache_path.is_file()
            and merge_cache_path.stat().st_size > 100_000
        ):
            dash_tmp_path = str(merge_cache_path)
            size = merge_cache_path.stat().st_size
            stream_kind = "hls_cache"
            stream_target = dash_tmp_path
        elif method == "HEAD":
            stream_kind = "hls_head"
            stream_target = ""
            size = 0
            size_known = False
        else:
            async def _merge_hls() -> str:
                merged_tmp = await _merge_hls_to_temp(
                    src.direct_url, src.direct_url_audio
                )
                _stash_merge_cache(settings, merge_cache_path, merged_tmp)
                _store_merge_cache_title(merge_cache_path, title)
                if merge_cache_path.is_file() and merge_cache_path.stat().st_size > 0:
                    return str(merge_cache_path)
                return merged_tmp

            try:
                dash_tmp_path = await _single_flight(
                    str(merge_cache_path), _merge_hls
                )
            except ProviderUnavailableError as e:
                await _invalidate_upstream(provider, media_id)
                raise HTTPException(status_code=502, detail={
                    "error": "upstream_unavailable",
                    "detail": str(e),
                })
            if dash_tmp_path == str(merge_cache_path):
                stream_kind = "hls_cache"
            else:
                stream_kind = "hls_temp"
                delete_dash_after = True
            size = os.path.getsize(dash_tmp_path)
            _guard_merged_size(settings, dash_tmp_path, size)
            stream_target = dash_tmp_path
    elif src.direct_url:
        # A playlist URL would otherwise be proxied as if it were the
        # media file, handing the client a tiny text manifest. Treat
        # it like the HLS branch: remux into a real MP4 first.
        if _url_is_manifest(src.direct_url):
            mime_type = "video/mp4"
            merge_cache_path = _merge_cache_path(settings, media_id, effective_height)
            if (
                merge_cache_path.is_file()
                and merge_cache_path.stat().st_size > 100_000
            ):
                dash_tmp_path = str(merge_cache_path)
                size = merge_cache_path.stat().st_size
                stream_kind = "hls_cache"
                stream_target = dash_tmp_path
            elif method == "HEAD":
                stream_kind = "hls_head"
                stream_target = ""
                size = 0
                size_known = False
            else:
                async def _merge_manifest() -> str:
                    merged_tmp = await _merge_hls_to_temp(src.direct_url, None)
                    _stash_merge_cache(settings, merge_cache_path, merged_tmp)
                    _store_merge_cache_title(merge_cache_path, title)
                    if merge_cache_path.is_file() and merge_cache_path.stat().st_size > 0:
                        return str(merge_cache_path)
                    return merged_tmp

                try:
                    dash_tmp_path = await _single_flight(
                        str(merge_cache_path), _merge_manifest
                    )
                except ProviderUnavailableError as e:
                    await _invalidate_upstream(provider, media_id)
                    raise HTTPException(status_code=502, detail={
                        "error": "upstream_unavailable",
                        "detail": str(e),
                    })
                if dash_tmp_path == str(merge_cache_path):
                    stream_kind = "hls_cache"
                else:
                    stream_kind = "hls_temp"
                    delete_dash_after = True
                size = os.path.getsize(dash_tmp_path)
                _guard_merged_size(settings, dash_tmp_path, size)
                stream_target = dash_tmp_path
        else:
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
    # An HLS HEAD has no reliable size (the remux has not run), so it
    # reports neither Content-Length nor Range support; the GET path
    # produces a complete, Range-capable MP4.
    start, end, status_code, content_range = 0, size - 1, 200, None
    if size_known and range_header:
        parsed = _parse_range(range_header, size)
        if parsed is not None:
            start, end = parsed
            status_code = 206
            content_range = f"bytes {start}-{end}/{size}"
    content_length = end - start + 1 if size_known else None

    # ── 6. Filename from metadata (best effort) ─────────────────────
    # The title was resolved in step 2a, it is reused here.
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
        "Accept-Ranges": "bytes" if size_known else "none",
        "Content-Type": mime_type,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": _content_disposition(filename),
    }
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    if content_range:
        headers["Content-Range"] = content_range

    chunk_size = settings.stream_chunk_size
    if method == "HEAD":
        # No body for HEAD. Release the slot now.
        await rate_limiter.release_stream(api_key.id, token)
        active_streams.dec()
        return StreamingResponse(
            iter(()), status_code=status_code, headers=headers,
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
            if stream_kind in (
                "dash_temp", "dash_cache", "hls_temp", "hls_cache",
            ):
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
            # now that the response has been fully streamed. Files
            # served from the merge cache must survive for reuse.
            if dash_tmp_path and delete_dash_after:
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
