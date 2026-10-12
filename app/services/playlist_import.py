"""Import playlists from a YouTube or Spotify playlist link.

YouTube public playlists are read with ``yt-dlp`` (no auth).
Spotify public playlists are read with the Spotify Web API using
the client-credentials flow (requires ``SPOTIFY_CLIENT_ID`` /
``SPOTIFY_CLIENT_SECRET``); private playlists need a user token
and are not supported.

Both return a playlist name plus a list of track drafts keyed by
the provider-prefixed media id (``yt:<video id>`` / ``sp:<track id>``)
so imported tracks stream through the normal provider registry.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_API = "https://api.spotify.com/v1"


class PlaylistImportError(Exception):
    """Raised when a playlist link cannot be imported."""


def detect_provider(url: str) -> Optional[str]:
    """Return ``"youtube"`` / ``"spotify"`` or ``None``."""
    u = (url or "").strip().lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "spotify.com" in u:
        return "spotify"
    return None


def _extract_spotify_playlist_id(url: str) -> Optional[str]:
    m = re.search(r"open\.spotify\.com/(?:embed/)?playlist/([A-Za-z0-9]+)", url)
    return m.group(1) if m else None


def _yt_extract(url: str) -> Optional[Dict[str, Any]]:
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


async def fetch_youtube_playlist(url: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Return ``(playlist_name, tracks)`` for a YouTube playlist URL."""
    try:
        info = await asyncio.to_thread(_yt_extract, url)
    except Exception as e:  # yt-dlp raises on unsupported/private URLs
        logger.warning("yt_playlist_import_failed", extra={"err": str(e)})
        raise PlaylistImportError(
            "Could not read that YouTube playlist (it may be private or the link is wrong)."
        ) from e
    if not info:
        raise PlaylistImportError("YouTube returned nothing for that link.")
    entries = info.get("entries") or []
    tracks: List[Dict[str, Any]] = []
    for e in entries:
        vid = e.get("id")
        if not vid:
            continue
        tracks.append({
            "media_id": f"yt:{vid}",
            "title": e.get("title") or "Unknown title",
            "artist": None,
        })
    if not tracks:
        raise PlaylistImportError("That YouTube playlist has no videos.")
    return str(info.get("title") or "YouTube Playlist"), tracks


async def fetch_spotify_playlist(
    url: str, client_id: Optional[str], client_secret: Optional[str]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Return ``(playlist_name, tracks)`` for a Spotify playlist URL."""
    if not client_id or not client_secret:
        raise PlaylistImportError(
            "Spotify playlist import requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
        )
    playlist_id = _extract_spotify_playlist_id(url)
    if not playlist_id:
        raise PlaylistImportError("Could not read the Spotify playlist id from that link.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            _SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
        )
        if resp.status_code != 200:
            raise PlaylistImportError("Spotify rejected the app credentials.")
        token = resp.json().get("access_token")

        pl = await client.get(
            f"{_SPOTIFY_API}/playlists/{playlist_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if pl.status_code != 200:
            raise PlaylistImportError(
                "Spotify playlist not found or not public."
            )
        name = str(pl.json().get("name") or "Spotify Playlist")

        tracks: List[Dict[str, Any]] = []
        offset = 0
        while True:
            resp = await client.get(
                f"{_SPOTIFY_API}/playlists/{playlist_id}/tracks",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "limit": 100,
                    "offset": offset,
                    "fields": "items(track(id,name,artists(name)))",
                },
            )
            data = resp.json()
            items = data.get("items") or []
            for it in items:
                t = it.get("track")
                if not t or not t.get("id"):
                    continue
                artists = ", ".join(
                    a.get("name", "") for a in (t.get("artists") or [])
                )
                tracks.append({
                    "media_id": f"sp:{t['id']}",
                    "title": t.get("name") or "Unknown title",
                    "artist": artists or None,
                })
            if len(items) < 100:
                break
            offset += 100
    if not tracks:
        raise PlaylistImportError("That Spotify playlist has no tracks.")
    return name, tracks
