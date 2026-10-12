"""JioSaavn metadata provider.

Resolves a JioSaavn track id to a YouTube video id by querying the public
``jiosaavn.com`` search endpoint and using the track title + artist to
search YouTube. Actual audio bytes come from YouTube — we never proxy
JioSaavn's own CDN.

No API key required: the search endpoint is public.
"""
from __future__ import annotations

from typing import Any, List, Optional

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

_SEARCH_URL = "https://www.jiosaavn.com/api.php"
_SEARCH_LIMIT = 5


def _extract_jiosaavn_id(media_id: str) -> str:
    s = (media_id or "").strip()
    if not s:
        raise MediaNotFoundError("empty jiosaavn media_id")
    if "/song/" in s:
        return s.split("/song/", 1)[1].split("/")[0].split("?")[0]
    return s


class JioSaavnProvider(MediaProvider):
    name = "jv"

    def __init__(self, youtube: YouTubeProvider) -> None:
        self._youtube = youtube

    @property
    def enabled(self) -> bool:
        return bool(self._youtube and self._youtube.enabled)

    async def _search(self, query: str) -> List[dict]:
        params = {
            "__call": "search.getResults",
            "q": query,
            "p": "0",
            "n": str(_SEARCH_LIMIT),
            "includeMetaTags": "0",
        }
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 iota-api"},
            ) as client:
                resp = await client.get(_SEARCH_URL, params=params)
        except httpx.HTTPError as e:
            logger.warning("jiosaavn_search_error", extra={"err": str(e)})
            return []
        if resp.status_code != 200:
            return []
        # The endpoint returns a JSON-like string; tolerate single-quoted
        # JSON by attempting a strict parse first and falling back.
        try:
            data: Any = resp.json()
        except Exception:
            return []
        songs = (data or {}).get("results") or []
        out: List[dict] = []
        for song in songs:
            title = song.get("title") or song.get("song")
            artist = song.get("primary_artists") or song.get("singers") or song.get("music")
            if not title:
                continue
            out.append({"title": title.strip(), "artist": (artist or "").strip()})
        return out

    async def _resolve_to_yt(self, media_id: str) -> Optional[MediaMetadata]:
        native_id = _extract_jiosaavn_id(media_id)
        # The api.php endpoint takes a query; if the caller passed a bare
        # id we cannot directly look it up without an additional call, so
        # we use the id as a search query (most JioSaavn ids are slugs).
        hits = await self._search(native_id.replace("-", " "))
        if not hits:
            return None
        first = hits[0]
        query = (
            f"{first['artist']} - {first['title']}"
            if first.get("artist") else first["title"]
        )
        results = await self._youtube.search(query, limit=_SEARCH_LIMIT)
        if not results:
            return None
        top = results[0]
        return MediaMetadata(
            media_id=top.media_id,
            title=first["title"],
            artist=first.get("artist") or top.artist,
            duration_seconds=top.duration_seconds,
            thumbnail_url=top.thumbnail_url,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        if not query or not query.strip():
            return []
        hits = await self._search(query)
        out: List[MediaMetadata] = []
        for h in hits:
            q = f"{h['artist']} - {h['title']}" if h.get("artist") else h["title"]
            results = await self._youtube.search(q, limit=1)
            if not results:
                continue
            top = results[0]
            out.append(MediaMetadata(
                media_id=top.media_id,
                title=h["title"],
                artist=h.get("artist") or top.artist,
                duration_seconds=top.duration_seconds,
                thumbnail_url=top.thumbnail_url,
                mime_type="audio/mpeg",
                storage_key="",
                provider=self.name,
            ))
            if len(out) >= limit:
                break
        return out

    async def get_info(self, media_id: str) -> MediaMetadata:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"jiosaavn: no info for {media_id}")
        return meta

    async def get_stream(self, media_id: str) -> StreamSource:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"jiosaavn: cannot resolve {media_id}")
        return await self._youtube.get_stream(meta.media_id)
