"""User library service: playlists, favourites, history, queue,
ratings, tags and derived stats.

All operations are scoped to ``api_key_id`` — the authenticated
API key acts as the user. Display fields are denormalized onto
each row; when a caller only supplies a ``media_id`` we
best-effort resolve the missing title/artist/… through the
provider registry so entries are pleasant to read even offline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.library import (
    Favourite,
    HistoryEntry,
    Playlist,
    PlaylistTrack,
    QueueItem,
    Rating,
    TrackTag,
)
from app.services.media_provider import MediaProvider
from app.services.playlist_import import (
    PlaylistImportError,
    detect_provider,
    fetch_spotify_playlist,
    fetch_youtube_playlist,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

_HISTORY_LIMIT = 200
_DEFAULT_TOP_LIMIT = 10


class LibraryService:
    def __init__(
        self,
        session: AsyncSession,
        provider: Optional[MediaProvider] = None,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
    ) -> None:
        self._session = session
        self._provider = provider
        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret

    # ── helpers ──────────────────────────────────────────────

    async def _playlist(self, api_key_id: int, playlist_id: int) -> Optional[Playlist]:
        result = await self._session.execute(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.api_key_id == api_key_id,
            )
        )
        return result.scalar_one_or_none()

    def _prefix(self, media_id: str) -> Optional[str]:
        return media_id.split(":", 1)[0] if ":" in media_id else None

    async def _resolve_meta(
        self,
        media_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fill in missing display fields, best-effort via the provider."""
        meta: Dict[str, Any] = {
            "title": title or "Unknown title",
            "artist": artist,
            "duration_seconds": duration_seconds,
            "thumbnail_url": thumbnail_url,
            "provider": self._prefix(media_id),
        }
        # Only round-trip to a provider when we actually need fields.
        if title and artist is not None and duration_seconds is not None:
            return meta
        if self._provider is None:
            return meta
        try:
            info = await self._provider.get_info(media_id)
        except Exception:
            return meta
        meta["title"] = title or info.title or "Unknown title"
        meta["artist"] = artist if artist is not None else info.artist
        meta["duration_seconds"] = (
            duration_seconds
            if duration_seconds is not None
            else info.duration_seconds
        )
        meta["thumbnail_url"] = thumbnail_url or info.thumbnail_url
        return meta

    # ── playlists ────────────────────────────────────────────

    async def create_playlist(
        self,
        api_key_id: int,
        name: str,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> Playlist:
        pl = Playlist(
            api_key_id=api_key_id,
            name=name,
            description=description,
            is_public=is_public,
        )
        self._session.add(pl)
        await self._session.commit()
        await self._session.refresh(pl)
        return pl

    async def list_playlists(self, api_key_id: int) -> List[Playlist]:
        result = await self._session.execute(
            select(Playlist)
            .where(Playlist.api_key_id == api_key_id)
            .order_by(Playlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_playlist(
        self, api_key_id: int, playlist_id: int
    ) -> Optional[Playlist]:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return None
        result = await self._session.execute(
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position, PlaylistTrack.added_at)
        )
        pl.tracks = list(result.scalars().all())  # type: ignore[attr-defined]
        return pl

    async def update_playlist(
        self,
        api_key_id: int,
        playlist_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> Optional[Playlist]:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return None
        if name is not None:
            pl.name = name
        if description is not None:
            pl.description = description
        if is_public is not None:
            pl.is_public = is_public
        await self._session.commit()
        await self._session.refresh(pl)
        return pl

    async def delete_playlist(self, api_key_id: int, playlist_id: int) -> bool:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return False
        await self._session.execute(
            delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
        )
        await self._session.delete(pl)
        await self._session.commit()
        return True

    async def add_track(
        self,
        api_key_id: int,
        playlist_id: int,
        media_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Optional[PlaylistTrack]:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return None
        # Idempotent: a duplicate returns the existing track.
        existing = await self._session.execute(
            select(PlaylistTrack).where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.media_id == media_id,
            )
        )
        existing_track = existing.scalar_one_or_none()
        if existing_track is not None:
            return existing_track
        meta = await self._resolve_meta(
            media_id, title, artist, duration_seconds, thumbnail_url
        )
        count = await self._session.scalar(
            select(func.count(PlaylistTrack.id)).where(
                PlaylistTrack.playlist_id == playlist_id
            )
        )
        track = PlaylistTrack(
            playlist_id=playlist_id,
            position=count or 0,
            media_id=media_id,
            title=meta["title"],
            artist=meta["artist"],
            duration_seconds=meta["duration_seconds"],
            thumbnail_url=meta["thumbnail_url"],
            provider=meta["provider"],
        )
        self._session.add(track)
        pl.track_count = (count or 0) + 1
        await self._session.commit()
        await self._session.refresh(track)
        return track

    async def remove_track(
        self, api_key_id: int, playlist_id: int, track_id: int
    ) -> bool:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return False
        result = await self._session.execute(
            select(PlaylistTrack).where(
                PlaylistTrack.id == track_id,
                PlaylistTrack.playlist_id == playlist_id,
            )
        )
        track = result.scalar_one_or_none()
        if track is None:
            return False
        await self._session.delete(track)
        pl.track_count = max(0, (pl.track_count or 0) - 1)
        await self._session.commit()
        return True

    async def reorder_tracks(
        self, api_key_id: int, playlist_id: int, track_ids: List[int]
    ) -> bool:
        pl = await self._playlist(api_key_id, playlist_id)
        if pl is None:
            return False
        result = await self._session.execute(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
        )
        by_id = {t.id: t for t in result.scalars().all()}
        if len(track_ids) != len(by_id) or any(
            tid not in by_id for tid in track_ids
        ):
            raise ValueError("track_ids must list every track exactly once")
        for position, tid in enumerate(track_ids):
            by_id[tid].position = position
        await self._session.commit()
        return True

    # ── playlist import ──────────────────────────────────────

    async def import_playlist(
        self, api_key_id: int, url: str, name: Optional[str] = None
    ) -> Playlist:
        provider = detect_provider(url)
        if provider == "youtube":
            resolved_name, tracks = await fetch_youtube_playlist(url)
        elif provider == "spotify":
            resolved_name, tracks = await fetch_spotify_playlist(
                url, self._spotify_client_id, self._spotify_client_secret
            )
        else:
            raise PlaylistImportError(
                "Unsupported link. Pass a YouTube or Spotify playlist URL."
            )
        pl = await self.create_playlist(
            api_key_id,
            name=name or resolved_name,
            description=f"Imported from {provider}",
        )
        for i, t in enumerate(tracks):
            self._session.add(
                PlaylistTrack(
                    playlist_id=pl.id,
                    position=i,
                    media_id=t["media_id"],
                    title=t.get("title") or "Unknown title",
                    artist=t.get("artist"),
                    provider=self._prefix(t["media_id"]),
                )
            )
        pl.track_count = len(tracks)
        await self._session.commit()
        await self._session.refresh(pl)
        return pl

    # ── favourites ───────────────────────────────────────────

    async def add_favourite(
        self,
        api_key_id: int,
        media_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Favourite:
        existing = await self._session.execute(
            select(Favourite).where(
                Favourite.api_key_id == api_key_id,
                Favourite.media_id == media_id,
            )
        )
        fav = existing.scalar_one_or_none()
        if fav is not None:
            return fav
        meta = await self._resolve_meta(
            media_id, title, artist, duration_seconds, thumbnail_url
        )
        fav = Favourite(
            api_key_id=api_key_id,
            media_id=media_id,
            title=meta["title"],
            artist=meta["artist"],
            duration_seconds=meta["duration_seconds"],
            thumbnail_url=meta["thumbnail_url"],
            provider=meta["provider"],
        )
        self._session.add(fav)
        await self._session.commit()
        await self._session.refresh(fav)
        return fav

    async def list_favourites(self, api_key_id: int) -> List[Favourite]:
        result = await self._session.execute(
            select(Favourite)
            .where(Favourite.api_key_id == api_key_id)
            .order_by(Favourite.created_at.desc())
        )
        return list(result.scalars().all())

    async def remove_favourite(self, api_key_id: int, media_id: str) -> bool:
        result = await self._session.execute(
            select(Favourite).where(
                Favourite.api_key_id == api_key_id,
                Favourite.media_id == media_id,
            )
        )
        fav = result.scalar_one_or_none()
        if fav is None:
            return False
        await self._session.delete(fav)
        await self._session.commit()
        return True

    async def is_favourite(self, api_key_id: int, media_id: str) -> bool:
        result = await self._session.execute(
            select(Favourite.id).where(
                Favourite.api_key_id == api_key_id,
                Favourite.media_id == media_id,
            )
        )
        return result.scalar_one_or_none() is not None

    # ── history ──────────────────────────────────────────────

    async def record_play(
        self,
        api_key_id: int,
        media_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> HistoryEntry:
        meta = await self._resolve_meta(
            media_id, title, artist, duration_seconds
        )
        entry = HistoryEntry(
            api_key_id=api_key_id,
            media_id=media_id,
            title=meta["title"],
            artist=meta["artist"],
            duration_seconds=meta["duration_seconds"],
            provider=meta["provider"],
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def list_history(self, api_key_id: int, limit: int = _HISTORY_LIMIT) -> List[HistoryEntry]:
        result = await self._session.execute(
            select(HistoryEntry)
            .where(HistoryEntry.api_key_id == api_key_id)
            .order_by(HistoryEntry.played_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def clear_history(self, api_key_id: int) -> int:
        result = await self._session.execute(
            delete(HistoryEntry).where(HistoryEntry.api_key_id == api_key_id)
        )
        await self._session.commit()
        return result.rowcount or 0

    # ── queue ────────────────────────────────────────────────

    async def add_to_queue(
        self,
        api_key_id: int,
        media_id: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> QueueItem:
        meta = await self._resolve_meta(media_id, title, artist, duration_seconds)
        count = await self._session.scalar(
            select(func.count(QueueItem.id)).where(QueueItem.api_key_id == api_key_id)
        )
        item = QueueItem(
            api_key_id=api_key_id,
            position=count or 0,
            media_id=media_id,
            title=meta["title"],
            artist=meta["artist"],
            duration_seconds=meta["duration_seconds"],
            provider=meta["provider"],
        )
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def list_queue(self, api_key_id: int) -> List[QueueItem]:
        result = await self._session.execute(
            select(QueueItem)
            .where(QueueItem.api_key_id == api_key_id)
            .order_by(QueueItem.position, QueueItem.added_at)
        )
        return list(result.scalars().all())

    async def remove_from_queue(self, api_key_id: int, item_id: int) -> bool:
        result = await self._session.execute(
            select(QueueItem).where(
                QueueItem.id == item_id, QueueItem.api_key_id == api_key_id
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            return False
        await self._session.delete(item)
        await self._session.commit()
        return True

    async def clear_queue(self, api_key_id: int) -> int:
        result = await self._session.execute(
            delete(QueueItem).where(QueueItem.api_key_id == api_key_id)
        )
        await self._session.commit()
        return result.rowcount or 0

    async def reorder_queue(self, api_key_id: int, item_ids: List[int]) -> bool:
        result = await self._session.execute(
            select(QueueItem).where(QueueItem.api_key_id == api_key_id)
        )
        by_id = {i.id: i for i in result.scalars().all()}
        if len(item_ids) != len(by_id) or any(i not in by_id for i in item_ids):
            raise ValueError("item_ids must list every queue item exactly once")
        for position, iid in enumerate(item_ids):
            by_id[iid].position = position
        await self._session.commit()
        return True

    # ── top tracks ───────────────────────────────────────────

    async def top_tracks(self, api_key_id: int, limit: int = _DEFAULT_TOP_LIMIT) -> List[Dict[str, Any]]:
        result = await self._session.execute(
            select(
                HistoryEntry.media_id,
                HistoryEntry.title,
                HistoryEntry.artist,
                func.count(HistoryEntry.id).label("play_count"),
            )
            .where(HistoryEntry.api_key_id == api_key_id)
            .group_by(HistoryEntry.media_id, HistoryEntry.title, HistoryEntry.artist)
            .order_by(func.count(HistoryEntry.id).desc())
            .limit(limit)
        )
        return [
            {
                "media_id": row.media_id,
                "title": row.title,
                "artist": row.artist,
                "play_count": row.play_count,
            }
            for row in result.all()
        ]

    # ── ratings ──────────────────────────────────────────────

    async def rate_track(
        self, api_key_id: int, media_id: str, rating: int
    ) -> Rating:
        result = await self._session.execute(
            select(Rating).where(
                Rating.api_key_id == api_key_id, Rating.media_id == media_id
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            row.rating = rating
            await self._session.commit()
            await self._session.refresh(row)
            return row
        row = Rating(api_key_id=api_key_id, media_id=media_id, rating=rating)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_rating(self, api_key_id: int, media_id: str) -> Optional[Rating]:
        result = await self._session.execute(
            select(Rating).where(
                Rating.api_key_id == api_key_id, Rating.media_id == media_id
            )
        )
        return result.scalar_one_or_none()

    async def remove_rating(self, api_key_id: int, media_id: str) -> bool:
        result = await self._session.execute(
            delete(Rating).where(
                Rating.api_key_id == api_key_id, Rating.media_id == media_id
            )
        )
        await self._session.commit()
        return bool(result.rowcount)

    # ── tags ─────────────────────────────────────────────────

    async def add_tag(self, api_key_id: int, media_id: str, tag: str) -> TrackTag:
        tag = tag.strip().lower()
        existing = await self._session.execute(
            select(TrackTag).where(
                TrackTag.api_key_id == api_key_id,
                TrackTag.media_id == media_id,
                TrackTag.tag == tag,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            return row
        row = TrackTag(api_key_id=api_key_id, media_id=media_id, tag=tag)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def remove_tag(self, api_key_id: int, media_id: str, tag: str) -> bool:
        tag = tag.strip().lower()
        result = await self._session.execute(
            delete(TrackTag).where(
                TrackTag.api_key_id == api_key_id,
                TrackTag.media_id == media_id,
                TrackTag.tag == tag,
            )
        )
        await self._session.commit()
        return bool(result.rowcount)

    async def list_tags(self, api_key_id: int, media_id: str) -> List[str]:
        result = await self._session.execute(
            select(TrackTag.tag)
            .where(
                TrackTag.api_key_id == api_key_id,
                TrackTag.media_id == media_id,
            )
            .order_by(TrackTag.tag)
        )
        return [r for r in result.scalars().all()]

    async def tracks_by_tag(self, api_key_id: int, tag: str) -> List[TrackTag]:
        tag = tag.strip().lower()
        result = await self._session.execute(
            select(TrackTag)
            .where(TrackTag.api_key_id == api_key_id, TrackTag.tag == tag)
            .order_by(TrackTag.created_at.desc())
        )
        return list(result.scalars().all())

    async def all_tags(self, api_key_id: int) -> List[str]:
        result = await self._session.execute(
            select(TrackTag.tag)
            .where(TrackTag.api_key_id == api_key_id)
            .distinct()
            .order_by(TrackTag.tag)
        )
        return [r for r in result.scalars().all()]

    # ── overview ─────────────────────────────────────────────

    async def overview(self, api_key_id: int) -> Dict[str, int]:
        async def _count(model, col) -> int:
            return int(
                await self._session.scalar(
                    select(func.count(model.id)).where(col == api_key_id)
                )
                or 0
            )

        return {
            "playlists": await _count(Playlist, Playlist.api_key_id),
            "favourites": await _count(Favourite, Favourite.api_key_id),
            "history": await _count(HistoryEntry, HistoryEntry.api_key_id),
            "queue": await _count(QueueItem, QueueItem.api_key_id),
            "ratings": await _count(Rating, Rating.api_key_id),
            "tags": await _count(TrackTag, TrackTag.api_key_id),
        }
