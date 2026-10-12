"""Pydantic models for the user library API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── shared track shape ─────────────────────────────────

class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    provider: Optional[str] = None


class TrackAdd(BaseModel):
    media_id: str = Field(..., min_length=1, max_length=512)
    title: Optional[str] = None
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None


class ReorderRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1)


# ── playlists ──────────────────────────────────────────

class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    is_public: bool = False


class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    is_public: Optional[bool] = None


class PlaylistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    track_count: int
    created_at: datetime
    updated_at: datetime


class PlaylistTrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    position: int
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    provider: Optional[str] = None
    added_at: datetime


class PlaylistDetail(PlaylistOut):
    model_config = ConfigDict(from_attributes=True)

    tracks: List[PlaylistTrackOut] = []


class ImportRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    name: Optional[str] = Field(None, max_length=256)


# ── favourites ─────────────────────────────────────────

class FavouriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    provider: Optional[str] = None
    created_at: datetime


class FavouriteCheck(BaseModel):
    media_id: str
    is_favourite: bool


# ── history ────────────────────────────────────────────

class HistoryRecord(BaseModel):
    media_id: str = Field(..., min_length=1, max_length=512)
    title: Optional[str] = None
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    provider: Optional[str] = None
    played_at: datetime


# ── queue ──────────────────────────────────────────────

class QueueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    position: int
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    provider: Optional[str] = None


# ── ratings ────────────────────────────────────────────

class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    rating: int
    updated_at: datetime


# ── tags ───────────────────────────────────────────────

class TagAdd(BaseModel):
    tag: str = Field(..., min_length=1, max_length=128)


class TrackTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: str
    tag: str
    created_at: datetime


# ── overview / top tracks ──────────────────────────────

class LibraryOverview(BaseModel):
    playlists: int
    favourites: int
    history: int
    queue: int
    ratings: int
    tags: int


class TopTrack(BaseModel):
    media_id: str
    title: str
    artist: Optional[str] = None
    play_count: int
