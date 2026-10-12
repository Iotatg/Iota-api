"""Apple Music catalog provider (via the public iTunes Search API).

Searches the iTunes catalog (no key required) and resolves the
actual audio stream via YouTube. The provider never proxies
Apple's own CDN.

API docs: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.services.media_provider import MediaMetadata
from app.services.youtube_backed_provider import YouTubeBackedProvider
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_API = "https://itunes.apple.com/search"
_LOOKUP_API = "https://itunes.apple.com/lookup"
_HTTP_TIMEOUT = 10.0


class AppleMusicProvider(YouTubeBackedProvider):
    name = "am"

    def __init__(self, youtube: YouTubeProvider) -> None:
        super().__init__(youtube)

    async def _search_native(self, query: str, limit: int) -> List[dict]:
        params = {
            "term": query,
            "media": "music",
            "entity": "song",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(_API, params=params)
        except httpx.HTTPError as e:
            logger.warning("applemusic_request_error", extra={"err": str(e)})
            return []
        if resp.status_code != 200:
            return []
        try:
            data: Any = resp.json()
        except ValueError:
            return []
        return [r for r in (data.get("results") or []) if isinstance(r, dict)]

    async def _lookup_native(self, media_id: str) -> Optional[dict]:
        # The dedicated lookup endpoint is reliable for id
        # lookups; the search endpoint's id parameter
        # returns an empty result set.
        params = {"id": media_id}
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(_LOOKUP_API, params=params)
        except httpx.HTTPError as e:
            logger.warning("applemusic_lookup_error", extra={"err": str(e)})
            return None
        if resp.status_code != 200:
            return None
        try:
            data: Any = resp.json()
        except ValueError:
            return None
        results = data.get("results") or []
        if not results:
            return None
        return results[0] if isinstance(results[0], dict) else None

    def _native_id(self, native: dict) -> Optional[str]:
        mid = native.get("trackId")
        return str(mid) if mid is not None else None

    def _to_meta(self, native: dict, media_id: str) -> MediaMetadata:
        title = str(native.get("trackName") or "Unknown title")
        artist = str(native.get("artistName") or "").strip()
        duration_ms = native.get("trackTimeMillis")
        duration = int(duration_ms) // 1000 if duration_ms else None
        art = native.get("artworkUrl100") or native.get("artworkUrl60")
        return MediaMetadata(
            media_id=media_id,
            title=title,
            artist=artist or None,
            duration_seconds=duration,
            thumbnail_url=str(art) if art else None,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )
