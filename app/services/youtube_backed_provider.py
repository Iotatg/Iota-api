"""Shared base for catalog providers that resolve native metadata to
YouTube streams.

A catalog provider searches a public music catalog (Deezer, Apple
Music, MusicBrainz, ...) and returns records keyed by the catalog's
own native id. The actual audio bytes always come from YouTube —
the provider never proxies the catalog's own CDN, mirroring the
existing JioSaavn / Spotify / SoundCloud design.

Subclasses implement three hooks:

- ``_search_native``  — native search, returns a list of dicts
- ``_lookup_native``  — single-record lookup by native id
- ``_to_meta``        — convert a native dict into :class:`MediaMetadata`

The base handles search / get_info / get_stream and the
YouTube resolution used to obtain the stream.
"""
from __future__ import annotations

import abc
from typing import List, Optional

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class YouTubeBackedProvider(MediaProvider, abc.ABC):
    """Catalog provider backed by YouTube for the audio stream."""

    name = "base"

    def __init__(self, youtube: YouTubeProvider) -> None:
        self._youtube = youtube

    @property
    def enabled(self) -> bool:
        return bool(self._youtube and self._youtube.enabled)

    # ── subclass hooks ────────────────────────────────────────────

    @abc.abstractmethod
    async def _search_native(self, query: str, limit: int) -> List[dict]:
        """Search the native catalog; return raw result dicts."""

    @abc.abstractmethod
    async def _lookup_native(self, media_id: str) -> Optional[dict]:
        """Fetch a single native record by id (None if not found)."""

    @abc.abstractmethod
    def _to_meta(self, native: dict, media_id: str) -> MediaMetadata:
        """Convert a native record dict into MediaMetadata."""

    @abc.abstractmethod
    def _native_id(self, native: dict) -> Optional[str]:
        """Return the catalog's native id for a record (None if absent)."""

    # ── shared resolution ─────────────────────────────────────────

    def _yt_query(self, native: dict, media_id: str) -> str:
        # Build the YouTube search query from the provider's own
        # metadata extraction (each _to_meta knows where its
        # catalog stores the artist — nested dict, flat string,
        # artist-credit list, artistName, …).
        meta = self._to_meta(native, media_id)
        return f"{meta.artist} - {meta.title}" if meta.artist else meta.title

    async def _resolve_stream(self, native: dict, media_id: str) -> StreamSource:
        """Resolve a native record to a YouTube stream source."""
        query = self._yt_query(native, media_id)
        if not query:
            raise MediaNotFoundError(
                f"{self.name}: native record has no title to resolve"
            )
        results = await self._youtube.search(query, limit=5)
        if not results:
            raise MediaNotFoundError(
                f"{self.name}: no YouTube match for {query!r}"
            )
        return await self._youtube.get_stream(results[0].media_id)

    # ── MediaProvider contract ────────────────────────────────────

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        if not query or not query.strip():
            return []
        native_results = await self._search_native(query.strip(), limit)
        out: List[MediaMetadata] = []
        for native in native_results:
            mid = self._native_id(native)
            if not mid:
                continue
            out.append(self._to_meta(native, mid))
            if len(out) >= limit:
                break
        return out

    async def get_info(self, media_id: str) -> MediaMetadata:
        native = await self._lookup_native(media_id)
        if not native:
            raise MediaNotFoundError(f"{self.name}: no info for {media_id}")
        return self._to_meta(native, media_id)

    async def get_stream(self, media_id: str) -> StreamSource:
        native = await self._lookup_native(media_id)
        if not native:
            raise MediaNotFoundError(f"{self.name}: cannot resolve {media_id}")
        return await self._resolve_stream(native, media_id)
