"""MusicBrainz catalog provider.

Searches the public MusicBrainz database (no key required)
and resolves the actual audio stream via YouTube. The
provider never proxies MusicBrainz's own data beyond the
metadata lookup.

MusicBrainz requires a descriptive User-Agent header with
contact information: https://musicbrainz.org/doc/XMLWebService
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.services.media_provider import MediaMetadata
from app.services.youtube_backed_provider import YouTubeBackedProvider
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_API = "https://musicbrainz.org/ws/2/recording/"
_HTTP_TIMEOUT = 10.0
_USER_AGENT = "iota-api/1.0 (https://example.com/iota; music-bot@example.com)"


class MusicBrainzProvider(YouTubeBackedProvider):
    name = "mb"

    def __init__(self, youtube: YouTubeProvider) -> None:
        super().__init__(youtube)

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": _USER_AGENT, "Accept": "application/json"}

    async def _search_native(self, query: str, limit: int) -> List[dict]:
        params = {
            "query": f'"{query}"',
            "fmt": "json",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(
                    _API, params=params, headers=self._headers()
                )
        except httpx.HTTPError as e:
            logger.warning("musicbrainz_request_error", extra={"err": str(e)})
            return []
        if resp.status_code != 200:
            return []
        try:
            data: Any = resp.json()
        except ValueError:
            return []
        return [r for r in (data.get("recordings") or []) if isinstance(r, dict)]

    async def _lookup_native(self, media_id: str) -> Optional[dict]:
        params = {"fmt": "json"}
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(
                    f"{_API}{media_id}", params=params, headers=self._headers()
                )
        except httpx.HTTPError as e:
            logger.warning("musicbrainz_lookup_error", extra={"err": str(e)})
            return None
        if resp.status_code != 200:
            return None
        try:
            data: Any = resp.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _native_id(self, native: dict) -> Optional[str]:
        mid = native.get("id")
        return str(mid) if mid is not None else None

    def _artist_name(self, native: dict) -> str:
        parts: List[str] = []
        for credit in native.get("artist-credit") or []:
            if isinstance(credit, dict) and credit.get("name"):
                parts.append(str(credit["name"]))
        return ", ".join(parts)

    def _to_meta(self, native: dict, media_id: str) -> MediaMetadata:
        title = str(native.get("title") or "Unknown title")
        artist = self._artist_name(native)
        length = native.get("length")
        duration = int(length) // 1000 if length else None
        return MediaMetadata(
            media_id=media_id,
            title=title,
            artist=artist or None,
            duration_seconds=duration,
            thumbnail_url=None,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )
