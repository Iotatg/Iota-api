"""On-demand audio repair for ``/stream/{id}?format=m4a|mp3``.

YouTube's premium audio (itag 140) ships as single-file DASH: an MP4
whose header boxes are ``ftyp dash`` + fragments. Browsers cope, but
many simple players and messengers refuse to inline-play it and save
the response as a file instead. This module asks ffmpeg (already in
the image) to rewrite the upstream URL into a universally playable
form:

- ``m4a``: bit-exact remux into progressive MP4 with the index at the
  front (``+faststart``), so seekable players stream instantly.
- ``mp3``: libmp3lame transcode, the most compatible format of all.

Repaired files land in the storage backend under ``fixed/`` and are
built once per track (per-key asyncio lock, FIFO eviction so the disk
stays bounded). Any failure falls back to the original stream — the
repair is strictly best-effort.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile
from collections import deque
from typing import Dict, Optional

from app.services.media_provider import StreamSource
from app.utils.logging import get_logger

logger = get_logger(__name__)

FIX_FORMATS = ("m4a", "mp3")
FIX_MIME = {"m4a": "audio/mp4", "mp3": "audio/mpeg"}

_FFMPEG_TIMEOUT = 180.0
_UA = "Mozilla/5.0 (compatible; iota-api)"
_KEEP_FIXED = 30
_locks: Dict[str, asyncio.Lock] = {}
_recent: deque = deque()


def _ffmpeg_args(fmt: str, url: str, out_path: str) -> list:
    base = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-user_agent", _UA,
        "-headers", "Referer: https://www.youtube.com/\r\n",
        "-i", url,
    ]
    if fmt == "m4a":
        return base + ["-vn", "-c:a", "copy", "-movflags", "+faststart",
                       "-f", "mp4", out_path]
    return base + ["-vn", "-c:a", "libmp3lame", "-q:a", "2",
                   "-f", "mp3", out_path]


async def _ffmpeg(fmt: str, url: str, out_path: str) -> Optional[str]:
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *_ffmpeg_args(fmt, url, out_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), _FFMPEG_TIMEOUT)
    except (asyncio.TimeoutError, FileNotFoundError) as e:
        if proc is not None:
            with contextlib.suppress(Exception):
                proc.kill()
        return f"{type(e).__name__}"
    if proc.returncode != 0:
        return (stderr or b"").decode(errors="ignore").strip()[-300:]
    return None


def fixed_key(media_id: str, fmt: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in media_id)
    return f"fixed/{safe}-{fmt}.{fmt}"


async def ensure_fixed_source(
    storage, media_id: str, src: StreamSource, fmt: str
) -> Optional[StreamSource]:
    """Return a storage-backed StreamSource for the repaired audio, or
    None when the repair cannot be done (caller keeps the original)."""
    if fmt not in FIX_FORMATS or not src.direct_url:
        return None
    key = fixed_key(media_id, fmt)
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    async with _locks[key]:
        if not await storage.exists(key):
            fd, tmp = tempfile.mkstemp(suffix=f".{fmt}")
            os.close(fd)
            ok = False
            try:
                err = await _ffmpeg(fmt, src.direct_url, tmp)
                if not err and os.path.getsize(tmp) > 0:
                    await storage.put(key, tmp)
                    ok = True
                else:
                    logger.warning("audio_fix_failed",
                                   extra={"media_id": media_id, "fmt": fmt,
                                          "stderr": str(err)[:300]})
            except Exception as e:  # storage errors must not kill the stream
                logger.warning("audio_fix_store_failed",
                               extra={"media_id": media_id, "err": str(e)})
            finally:
                with contextlib.suppress(OSError):
                    os.remove(tmp)
            if not ok:
                return None
            _recent.append(key)
            await _evict_old(storage)
        return StreamSource(
            storage_key=key,
            size_bytes=0,
            mime_type=FIX_MIME[fmt],
        )


async def _evict_old(storage) -> None:
    """Best-effort FIFO cleanup of repair files (bounded disk use)."""
    base = getattr(storage, "base", None)
    while len(_recent) > _KEEP_FIXED:
        old = _recent.popleft()
        _locks.pop(old, None)
        if base is None:
            continue
        path = os.path.join(str(base), old)
        if path.startswith(str(base)):
            with contextlib.suppress(OSError):
                os.remove(path)
