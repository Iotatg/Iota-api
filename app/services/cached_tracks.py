"""Bundled catalog of pre-hosted track renditions (last-resort playback).

The image ships ``data/cached_tracks.json`` — a sanitized, host-
allowlisted index built by ``scripts/build_cached_index.py`` from a
third-party catalog dump. When YouTube refuses a video entirely
(rotation exhausted, breaker open), the stream routes resolve the 11-
char id against this index and proxy the rendition through our own
egress, so clients only ever talk to us; the origin host never appears
in any response body or header.

Security posture:
- only catalog-pinned https URLs on a fixed allowlist host are fetched;
- no redirects are followed by the sniffing client;
- requests carry a generic browser UA and no identifying headers;
- sniff results live in a small in-memory TTL cache only — nothing is
  written to disk.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_HOST = "files.catbox.moe"
_URL_RE = re.compile(
    rf"^https://{re.escape(ALLOWED_HOST)}/[A-Za-z0-9 _-]{{4,32}}\.(mp3|m4a|mp4)$",
    re.IGNORECASE,
)
_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "cached_tracks.json"
_SNIFF_MAX_ENTRIES = 512
_SNIFF_TTL_SECONDS = 6 * 3600
_SNIFF_BYTES = 12
_GENERIC_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_entries: Optional[dict[str, dict]] = None
_sniff_cache: dict[str, tuple[float, str]] = {}

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _load_index() -> dict[str, dict]:
    global _entries
    if _entries is not None:
        return _entries
    table: dict[str, dict] = {}
    try:
        raw = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("cached_index_unavailable", extra={"err": str(exc)[:200]})
        raw = []
    for item in raw:
        vid, url = item.get("id", ""), item.get("url", "")
        if not _ID_RE.fullmatch(vid) or not _URL_RE.fullmatch(url):
            continue
        table.setdefault(vid, item)
    _entries = table
    return _entries


def is_enabled() -> bool:
    return os.getenv("IOTA_CACHED_FALLBACK", "1").strip().lower() not in ("0", "false", "off")


def lookup(video_id: str) -> Optional[dict]:
    """Return the pinned catalog entry for a YouTube video id, if any."""
    if not video_id:
        return None
    return _load_index().get(video_id)


def index_size() -> int:
    return len(_load_index())


def _sniff_mime(magic: bytes, fallback: str) -> str:
    if magic.startswith(b"ID3") or magic[:1] == b"\xff":
        return "audio/mpeg"
    if magic[4:8] == b"ftyp":
        # mp3/.m4a-labelled files are really DASH m4a; .mp4 entries may
        # genuinely be video — trust the catalog only for those.
        return fallback if fallback == "video/mp4" else "audio/mp4"
    return fallback


async def refine_mime(entry: dict) -> str:
    """Best-effort container sniff so mislabelled renditions stream
    with an honest content-type. Falls back to the catalog guess."""
    url = entry.get("url", "")
    fallback = entry.get("mime") or "application/octet-stream"
    now = time.time()
    cached = _sniff_cache.get(url)
    if cached and cached[0] > now:
        return cached[1]
    mime = fallback
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(6.0, connect=4.0), follow_redirects=False
        ) as client:
            resp = await client.get(
                url, headers={"User-Agent": _GENERIC_UA, "Range": "bytes=0-11"}
            )
            if resp.status_code in (200, 206):
                mime = _sniff_mime(resp.content[:_SNIFF_BYTES], fallback)
    except Exception as exc:  # noqa: BLE001 — sniff is opportunistic
        logger.debug("cached_sniff_failed", extra={"err": str(exc)[:120]})
    if len(_sniff_cache) >= _SNIFF_MAX_ENTRIES:
        _sniff_cache.clear()
    _sniff_cache[url] = (now + _SNIFF_TTL_SECONDS, mime)
    return mime
