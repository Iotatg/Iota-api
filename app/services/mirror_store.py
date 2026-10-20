"""Self-heal media mirror on the litterbox file host (72h retention).

When a YouTube track is served successfully through the proxy path,
the exact bytes we already delivered are uploaded (fire-and-forget,
serialised) to litterbox — the same catbox-family host the offline
catalog uses — and indexed by video id. Later requests resolve from
the mirror *before* touching YouTube at all, which keeps the egress
IP cool and answers repeated plays instantly.

Safety invariants mirror the offline catalog:
- only URLs we received from the upload API, revalidated against a
  strict host/extension allowlist, ever enter the index;
- clients never see the mirror host: serving still goes through
  StreamProxy with a generic browser UA;
- index entries carry an expiry and are dropped on load/read after
  it, so a purged mirror degrades gracefully to the normal tiers;
- the mirror is opt-in: ``IOTA_MIRROR=1`` enables reading *and*
  writing, the default is off because it ships user traffic to a
  third-party file host.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import random
import re
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.services.media_provider import StreamSource
from app.utils.logging import get_logger

logger = get_logger(__name__)

_UPLOAD_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
_TTL_SECONDS = 72 * 3600
_SAFETY_MARGIN = 60 * 60  # retire entries an hour before server-side purge
_MAX_MIRROR_BYTES = 64 * 1024 * 1024
#: Public alias for callers deciding whether to tee bytes.
MAX_MIRROR_BYTES = _MAX_MIRROR_BYTES

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_MIRROR_URL_RE = re.compile(
    r"^https://litter\.catbox\.moe/[a-z0-9]{5,12}\.(mp3|m4a|aac|ogg|webm|mp4|mov)$"
)

_EXT_BY_MIME = {
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
}

_INDEX_PATH = Path(
    os.getenv(
        "IOTA_MIRROR_INDEX",
        str(Path(__file__).resolve().parents[2] / "data" / "mirror_index.json"),
    )
)

_entries: Optional[dict] = None
_lock = asyncio.Lock()
_sem = asyncio.Semaphore(1)
_tasks: set = set()


#: Global pause after an upload failure: never re-probe the host with a
#: new upload while it is unhappy (roughly one retry per cooldown window).
_BACKOFF_SECONDS = 30 * 60
_cooldown_until = 0.0


def _store_cooldown_active() -> bool:
    return time.time() < _cooldown_until


def _store_note_failure() -> None:
    global _cooldown_until
    _cooldown_until = time.time() + _BACKOFF_SECONDS


def is_enabled() -> bool:
    """The mirror ships traffic to a third-party host, so it stays off
    until the deployment opts in with ``IOTA_MIRROR=1``."""
    return os.getenv("IOTA_MIRROR", "0") == "1"


def _video_id(media_id: str) -> str:
    rest = media_id.split(":", 1)[1] if ":" in media_id else media_id
    return rest if _YOUTUBE_ID_RE.fullmatch(rest) else ""


def _load() -> dict:
    global _entries
    if _entries is not None:
        return _entries
    table: dict = {}
    now = time.time()
    try:
        raw = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for vid, entry in raw.items():
                if (
                    _YOUTUBE_ID_RE.fullmatch(str(vid))
                    and isinstance(entry, dict)
                    and _MIRROR_URL_RE.fullmatch(str(entry.get("url", "")))
                    and isinstance(entry.get("expires_at"), (int, float))
                    and entry["expires_at"] - now > 0
                ):
                    table[str(vid)] = entry
    except (OSError, ValueError):
        pass
    _entries = table
    return _entries


def _persist(table: dict) -> None:
    try:
        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _INDEX_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(table), encoding="utf-8")
        os.replace(tmp, _INDEX_PATH)
    except OSError:
        logger.warning("mirror_index_persist_failed")


def entry_for(media_id: str, kind: str) -> Optional[dict]:
    """A live mirror entry matching the media id and kind, if any."""
    if not is_enabled():
        return None
    vid = _video_id(media_id)
    if not vid:
        return None
    entry = _load().get(vid)
    if entry is None:
        return None
    if entry.get("expires_at", 0) - time.time() <= _SAFETY_MARGIN:
        return None
    if kind == "video" and not str(entry.get("url", "")).endswith((".mp4", ".mov", ".webm")):
        return None
    if kind == "audio" and str(entry.get("url", "")).endswith((".mp4", ".mov")):
        pass  # audio container also plays in kind=audio requests
    return entry


def stream_source(media_id: str, kind: str) -> Optional[StreamSource]:
    """A ready-to-serve source for a mirrored track, or None."""
    entry = entry_for(media_id, kind)
    if entry is None:
        return None
    logger.info(
        "stream_failover",
        extra={"via": "mirror", "video": media_id, "kind": kind},
    )
    return StreamSource(
        storage_key=f"mirror/{_video_id(media_id)}",
        size_bytes=0,
        mime_type=entry.get("mime", "application/octet-stream"),
        direct_url=entry["url"],
    )


async def _upload(data: bytes, ext: str, mime: str, attempts: int = 3) -> Optional[str]:
    """Push bytes to the mirror host, returning the validated URL.

    The host intermittently answers fresh uploads with HTTP 500 (its
    own backend, unrelated to our request), so brief retries are the
    correct remedy. The system curl binary is used deliberately: it
    keeps a consistent UA/TLS fingerprint on every attempt.
    """
    for attempt in range(attempts):
        fd, path = tempfile.mkstemp(suffix=f".{ext}")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            proc = await asyncio.create_subprocess_exec(
                "curl", "-sS", "--max-time", "180",
                "-F", "reqtype=fileupload",
                "-F", "time=72h",
                "-F", f"fileToUpload=@{path};type={mime}",
                _UPLOAD_URL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=200)
            except asyncio.TimeoutError:
                proc.kill()
                stdout = b""
        finally:
            with contextlib.suppress(OSError):
                os.unlink(path)
        if proc.returncode == 0 and stdout:
            url = stdout.decode(errors="ignore").strip()
            if _MIRROR_URL_RE.fullmatch(url):
                return url
        if attempt < attempts - 1:
            await asyncio.sleep(15 * (attempt + 1))
    return None


async def _store(video_id: str, kind: str, mime: str, data: bytes) -> None:
    ext = _EXT_BY_MIME.get((mime or "").split(";")[0].strip(), "mp3")
    async with _sem:
        table = _load()
        existing = table.get(video_id)
        if existing and existing.get("expires_at", 0) - time.time() > _SAFETY_MARGIN:
            return
        url = await _upload(data, ext, mime)
        if url is None or not _MIRROR_URL_RE.fullmatch(url):
            _store_note_failure()
            logger.info("mirror_upload_failed", extra={"video": video_id})
            return
        table[video_id] = {
            "url": url,
            "kind": kind,
            "mime": mime,
            "size": len(data),
            "expires_at": time.time() + _TTL_SECONDS - _SAFETY_MARGIN * random.uniform(0.8, 1.2),
        }
        _persist(table)
        logger.info(
            "mirror_stored",
            extra={"video": video_id, "kind": kind, "bytes": len(data)},
        )


def invalidate(media_id: str) -> None:
    """Drop a mirror entry that failed to deliver (self-heal).

    A purged or degraded litter file must not keep shadowing the
    healthy provider path; it will be re-mirrored on the next
    successful full delivery."""
    vid = _video_id(media_id)
    if not vid:
        return
    table = _load()
    if table.pop(vid, None) is not None:
        _persist(table)
        logger.info("mirror_invalidated", extra={"video": vid})


def enqueue_mirror(media_id: str, kind: str, mime: str, data: bytes) -> None:
    """Fire-and-forget mirror of already-delivered bytes (never raises)."""
    if not is_enabled():
        return
    vid = _video_id(media_id)
    if not vid or not data or not mime.startswith(("audio/", "video/")):
        return
    if len(data) > _MAX_MIRROR_BYTES or _store_cooldown_active():
        return

    async def _run() -> None:
        try:
            await _store(vid, kind, mime, data)
        except Exception:
            logger.debug("mirror_store_error", extra={"video": vid})

    try:
        task = asyncio.create_task(_run())
    except RuntimeError:  # no running loop (sync test context)
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
