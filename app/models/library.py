"""User library ORM models.

A user library is a set of personal collections built on top of the
media catalog: playlists, favourites, listening history, a play queue,
track ratings and tags. Every row is scoped to ``api_keys.id`` — the
authenticated API key acts as the user, so there is no separate user
table.

Display fields (title, artist, duration, thumbnail) are denormalized
onto each row so that listing a playlist / favourites / queue never
re-calls a provider, and so entries survive even if a provider later
goes offline.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Prefixed media ids (e.g. "yt:dQw4w9WgXcQ", "mb:<uuid>") can be
# longer than the bare ids the Media table stores, so library rows
# use a wider column.
MEDIA_ID_LEN = 512


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    track_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Playlist id={self.id} name={self.name!r} tracks={self.track_count}>"


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="Unknown title")
    artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("playlist_id", "media_id", name="uq_playlist_track"),
    )

    def __repr__(self) -> str:
        return f"<PlaylistTrack id={self.id} playlist={self.playlist_id} media={self.media_id!r}>"


class Favourite(Base):
    __tablename__ = "favourites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="Unknown title")
    artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("api_key_id", "media_id", name="uq_favourite"),
    )

    def __repr__(self) -> str:
        return f"<Favourite id={self.id} media={self.media_id!r}>"


class HistoryEntry(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="Unknown title")
    artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<HistoryEntry id={self.id} media={self.media_id!r}>"


class QueueItem(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="Unknown title")
    artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<QueueItem id={self.id} pos={self.position} media={self.media_id!r}>"


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("api_key_id", "media_id", name="uq_rating"),
    )

    def __repr__(self) -> str:
        return f"<Rating id={self.id} media={self.media_id!r} stars={self.rating}>"


class TrackTag(Base):
    __tablename__ = "track_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    media_id: Mapped[str] = mapped_column(String(MEDIA_ID_LEN), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("api_key_id", "media_id", "tag", name="uq_track_tag"),
    )

    def __repr__(self) -> str:
        return f"<TrackTag id={self.id} media={self.media_id!r} tag={self.tag!r}>"
