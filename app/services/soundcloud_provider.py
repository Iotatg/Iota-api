"""SoundCloud metadata provider.

Resolves a SoundCloud track URL or id to a YouTube video id via the public
``soundcloud.com/oembed`` endpoint (no auth) and the track title. Actual
audio bytes come from YouTube.

streaming is delegated to :class:`YouTubeProvider`; the provider never
touches the audio stream itself.
"""
from __future__ import annotations

from typing import List, Optional

import httpx

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_OEMBED_URL = "https://soundcloud.com/oembed"
_SEARCH_LIMIT = 5


def _extract_soundcloud_id(media_id: str) -> str:
    s = (media_id or "").strip()
    if not s:
        raise MediaNotFoundError("empty soundcloud media_id")
    # SoundCloud ids look like ``<user>-<slug>``; we keep whatever the
    # caller gave us as the "id" and let oEmbed resolve the URL.
    return s


class SoundCloudProvider(MediaProvider):
    name = "sc"

    def __init__(self, youtube: YouTubeProvider) -> None:
        self._youtube = youtube

    @property
    def enabled(self) -> bool:
        return bool(self._youtube and self._youtube.enabled)

    async def _oembed(self, soundcloud_url: str) -> Optional[dict]:
        params = {"url": soundcloud_url, "format": "json"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(_OEMBED_URL, params=params)
        except httpx.HTTPError as e:
            logger.warning("soundcloud_oembed_error", extra={"err": str(e)})
            return None
        if resp.status_code != 200:
            return None
        return resp.json() or None

    async def _resolve_to_yt(self, media_id: str) -> Optional[MediaMetadata]:
        native_id = _extract_soundcloud_id(media_id)
        if native_id.startswith("http"):
            url = native_id
        else:
            url = f"https://soundcloud.com/{native_id}"
        info = await self._oembed(url)
        if not info:
            return None
        title = info.get("title")
        if not title:
            return None
        artist = info.get("author_name") or ""
        query = f"{artist} - {title}" if artist else title
        results = await self._youtube.search(query, limit=_SEARCH_LIMIT)
        if not results:
            return None
        first = results[0]
        return MediaMetadata(
            media_id=first.media_id,
            title=title,
            artist=artist or first.artist,
            duration_seconds=first.duration_seconds,
            thumbnail_url=first.thumbnail_url or info.get("thumbnail_url"),
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        if not query or not query.strip():
            return []
        return await self._youtube.search(query, limit=limit)

    async def get_info(self, media_id: str) -> MediaMetadata:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"soundcloud: no info for {media_id}")
        return meta

    async def get_stream(self, media_id: str) -> StreamSource:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"soundcloud: cannot resolve {media_id}")
        return await self._youtube.get_stream(meta.media_id)
