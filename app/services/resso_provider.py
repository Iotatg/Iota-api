"""Resso catalog provider.

Attempts to search the public Resso catalog API and
resolves the actual audio stream via YouTube. Resso's
API is key-gated in many regions; when the endpoint is
unreachable the provider degrades gracefully (returns no
results) without affecting the other providers.

The provider never proxies Resso's own CDN.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.services.media_provider import MediaMetadata
from app.services.youtube_backed_provider import YouTubeBackedProvider
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_API = "https://api-resso.boomplay.com/v1.0"
_HTTP_TIMEOUT = 10.0


class RessoProvider(YouTubeBackedProvider):
    name = "rs"

    def __init__(self, youtube: YouTubeProvider) -> None:
        super().__init__(youtube)

    async def _get(self, path: str, params: Dict[str, Any]) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(f"{_API}/{path}", params=params)
        except httpx.HTTPError as e:
            logger.warning("resso_request_error", extra={"err": str(e)})
            return None
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    async def _search_native(self, query: str, limit: int) -> List[dict]:
        data = await self._get("search", {"q": query, "limit": limit})
        if not data:
            return []
        results = data.get("data") or data.get("results") or []
        return [r for r in results if isinstance(r, dict)]

    async def _lookup_native(self, media_id: str) -> Optional[dict]:
        data = await self._get(f"songs/{media_id}", {})
        if not data:
            return None
        return data.get("data") or data.get("song") or data

    def _native_id(self, native: dict) -> Optional[str]:
        mid = native.get("id") or native.get("song_id")
        return str(mid) if mid is not None else None

    def _to_meta(self, native: dict, media_id: str) -> MediaMetadata:
        title = str(
            native.get("title") or native.get("name") or "Unknown title"
        )
        artist = str(
            native.get("artist") or native.get("artist_name") or ""
        ).strip()
        duration = native.get("duration") or native.get("duration_seconds")
        return MediaMetadata(
            media_id=media_id,
            title=title,
            artist=artist or None,
            duration_seconds=int(duration) if duration else None,
            thumbnail_url=str(native.get("cover") or "") or None,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )
