"""Spotify metadata provider.

Resolves Spotify track/album/playlist URLs to a YouTube video id via the
public ``open.spotify.com/oembed`` endpoint (no auth) and the optional
``spotipy`` library when ``SPOTIFY_CLIENT_ID`` / ``SPOTIFY_CLIENT_SECRET``
are set. The actual audio bytes come from YouTube.

streaming is delegated to :class:`YouTubeProvider`; the provider never
touches the audio stream itself.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import httpx

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)
from app.config import get_settings
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)

_OEMBED_URL = "https://open.spotify.com/oembed"
_SEARCH_LIMIT = 5


def _extract_spotify_id(media_id: str) -> str:
    """Accept either a bare spotify id or a full URL; return the bare id."""
    s = (media_id or "").strip()
    if not s:
        raise MediaNotFoundError("empty spotify media_id")
    if "open.spotify.com" in s:
        # /track/<id>, /album/<id>, /playlist/<id>
        for prefix in ("/track/", "/album/", "/playlist/"):
            if prefix in s:
                return s.split(prefix, 1)[1].split("?")[0].split("/")[0]
    return s


class SpotifyProvider(MediaProvider):
    name = "sp"

    def __init__(
        self,
        youtube: YouTubeProvider,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self._youtube = youtube
        self._client_id = client_id
        self._client_secret = client_secret
        self._spotipy = None
        # The spotify → youtube resolution is a slow search, the answer is
        # kept for a while so the info and the stream of one track do not
        # pay for it twice.
        self._resolve_cache: Dict[str, Tuple[float, MediaMetadata]] = {}
        self._resolve_cache_ttl = float(
            get_settings().metadata_cache_ttl or 0
        )
        if client_id and client_secret:
            try:
                import spotipy  # type: ignore
                from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore
                self._spotipy = spotipy.Spotify(
                    auth_manager=SpotifyClientCredentials(
                        client_id=client_id, client_secret=client_secret
                    )
                )
            except Exception as e:
                logger.warning("spotipy_init_failed", extra={"err": str(e)})
                self._spotipy = None

    @property
    def enabled(self) -> bool:
        # oEmbed is public; we only need YouTube to actually stream.
        return bool(self._youtube and self._youtube.enabled)

    async def _oembed(self, spotify_url: str) -> Optional[dict]:
        params = {"url": spotify_url}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(_OEMBED_URL, params=params)
        except httpx.HTTPError as e:
            logger.warning("spotify_oembed_error", extra={"err": str(e)})
            return None
        if resp.status_code != 200:
            return None
        return resp.json() or None

    def _cache_get(self, media_id: str) -> Optional[MediaMetadata]:
        """Return the cached resolution of a track, if there is one."""
        if self._resolve_cache_ttl <= 0:
            return None
        entry = self._resolve_cache.get(media_id)
        if entry is None:
            return None
        expires, meta = entry
        if time.monotonic() > expires:
            self._resolve_cache.pop(media_id, None)
            return None
        return meta

    def _cache_put(self, media_id: str, meta: MediaMetadata) -> None:
        """Keep the resolution of a track for the next request."""
        if self._resolve_cache_ttl <= 0:
            return
        if len(self._resolve_cache) >= 5000:
            now = time.monotonic()
            for key, (expires, _) in list(self._resolve_cache.items()):
                if now > expires:
                    self._resolve_cache.pop(key, None)
        self._resolve_cache[media_id] = (time.monotonic() + self._resolve_cache_ttl, meta)

    async def _resolve_to_yt(self, media_id: str) -> Optional[MediaMetadata]:
        cached = self._cache_get(media_id)
        if cached is not None:
            return cached

        native_id = _extract_spotify_id(media_id)
        spotify_url = f"https://open.spotify.com/track/{native_id}"
        info = None
        if self._spotipy is not None:
            try:
                track = self._spotipy.track(native_id)
                if track:
                    info = {
                        "title": track.get("name"),
                        "channel": ", ".join(
                            a.get("name", "") for a in (track.get("artists") or [])
                        ) or None,
                    }
            except Exception as e:
                logger.warning("spotipy_track_failed", extra={"err": str(e)})
        if info is None:
            oembed = await self._oembed(spotify_url)
            if oembed:
                info = {
                    "title": oembed.get("title"),
                    "channel": None,
                }
        if not info or not info.get("title"):
            return None
        artist = info.get("channel") or ""
        query = f"{artist} - {info['title']}" if artist else info["title"]
        results = await self._youtube.search(query, limit=_SEARCH_LIMIT)
        if not results:
            return None
        first = results[0]
        meta = MediaMetadata(
            media_id=first.media_id,
            title=info["title"],
            artist=artist or first.artist,
            duration_seconds=first.duration_seconds,
            thumbnail_url=first.thumbnail_url,
            mime_type="audio/mpeg",
            storage_key="",
            provider=self.name,
        )
        self._cache_put(media_id, meta)
        return meta

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        if not query or not query.strip():
            return []
        # Spotify search requires auth; delegate to YouTube search but tag
        # results as Spotify-sourced. (v1 limitation: we do not return
        # Spotify-native ids here, only YT-backed metadata.)
        return await self._youtube.search(query, limit=limit)

    async def get_info(self, media_id: str) -> MediaMetadata:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"spotify: no info for {media_id}")
        return meta

    async def get_stream(self, media_id: str) -> StreamSource:
        meta = await self._resolve_to_yt(media_id)
        if meta is None:
            raise MediaNotFoundError(f"spotify: cannot resolve {media_id}")
        return await self._youtube.get_stream(meta.media_id)
