"""Pydantic models for media metadata."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MediaInfo(BaseModel):
    """Public-facing media metadata."""

    model_config = ConfigDict(from_attributes=True)

    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: str = "audio/mpeg"
    provider: str
    views: Optional[int] = Field(
        None, description="View count when the source exposes it (e.g. YouTube)"
    )
    likes: Optional[int] = None


class SearchResult(BaseModel):
    query: str
    count: int
    results: List[MediaInfo]


class StreamInfo(BaseModel):
    """Returned in JSON form by /info when you want the full stream location."""

    model_config = ConfigDict(from_attributes=True)

    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    size_bytes: Optional[int] = None
    mime_type: str = "audio/mpeg"
    stream_url: str = Field(..., description="Relative or absolute URL to stream this media")
    supports_range: bool = True
