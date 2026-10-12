"""Native failover when the primary provider is down.

When YouTube bot-blocks our egress IP, ``get_stream`` fails and the
caller would 503. ``YouTubeProvider.rotation_stream`` re-resolves the
same video through cookie-less Innertube player clients that are
flagged independently (tv, web_embedded, ...), so playback survives an
IP-level block entirely inside our own stack — no third-party relays.

Everything here is fail-soft: any error yields ``None`` so the caller
keeps its original error semantics. Only ids addressing a YouTube
video are considered.
"""
from __future__ import annotations

import re

from app.services import cached_tracks, mirror_store
from app.services.media_provider import StreamSource
from app.services.provider_registry import find_youtube_provider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _youtube_video_id(media_id: str) -> str:
    """The 11-char video id iff ``media_id`` addresses a YouTube video."""
    rest = media_id.split(":", 1)[1] if ":" in media_id else media_id
    return rest if _YOUTUBE_ID_RE.fullmatch(rest) else ""


async def _cached_source(media_id: str, kind: str) -> StreamSource | None:
    """Rendition from the bundled offline catalog, proxied via us."""
    if not cached_tracks.is_enabled():
        return None
    entry = cached_tracks.lookup(media_id)
    if entry is None:
        return None
    if kind == "video" and entry.get("ext") != "mp4":
        return None
    mime = await cached_tracks.refine_mime(entry)
    logger.info(
        "stream_failover",
        extra={"via": "cached_catalog", "video": media_id, "kind": kind},
    )
    return StreamSource(
        storage_key=f"cached/{media_id}",
        size_bytes=0,
        mime_type=mime,
        direct_url=entry["url"],
    )


async def relay_source(
    provider, media_id: str, kind: str = "audio"
) -> StreamSource | None:
    if ":" in media_id and not media_id.startswith("yt:"):
        return None
    vid = _youtube_video_id(media_id)
    if not vid:
        return None
    yt = find_youtube_provider(provider)
    if yt is not None and hasattr(yt, "rotation_stream"):
        source = await yt.rotation_stream(vid, kind=kind)
        if source is not None:
            logger.info("stream_failover", extra={"via": "client_rotation",
                                                  "video": vid, "kind": kind})
            return source
    mirror = mirror_store.stream_source(media_id, kind)
    if mirror is not None:
        return mirror
    return await _cached_source(vid, kind)
