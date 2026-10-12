"""Deezer catalog provider.

Searches the public Deezer API (no key required) and resolves
the actual audio stream via YouTube. The provider never
proxies Deezer's own CDN.

API docs: https://developers.deezer.com/api
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.services.media_provider import MediaMetadata
from app.services.youtube_backed_provider import YouTubeBackedProvider
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_API = "https://api.deezer.com"
_HTTP_TIMEOUT = 10.0


def _pick_artist(node: Any) -> str:
    if isinstance(node, dict):
        return str(node.get("name") or "").strip()
    return ""


class DeezerProvider(YouTubeBackedProvider):
    name = "dz"

    def __init__(self, youtube: YouTubeProvider) -> None:
        super().__init__(youtube)

    async def _get(self, path: str, params: Dict[str, Any]) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(f"{_API}/{path}", params=params)
        except httpx.HTTPError as e:
            logger.warning("deezer_request_error", extra={"err": str(e)})
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
        return [r for r in (data.get("data") or []) if isinstance(r, dict)]

    async def _lookup_native(self, media_id: str) -> Optional[dict]:
        data = await self._get(f"track/{media_id}", {})
        if not data or "error" in data:
            return None
        return data

    def _native_id(self, native: dict) -> Optional[str]:
        mid = native.get("id")
        return str(mid) if mid is not None else None

    def _to_meta(self, native: dict, media_id: str) -> MediaMetadata:
        artist = _pick_artist(native.get("artist"))
        album = native.get("album") or {}
        return MediaMetadata(
            media_id=media_id,
            title=str(native.get("title") or "Unknown title"),
            artist=artist or None,
            duration_seconds=int(native.get("duration") or 0) or None,
            thumbnail_url=str(album.get("cover") or "") or None,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )
