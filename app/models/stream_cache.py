"""StreamCache ORM model.

Persists resolved upstream stream URLs so the URL cache survives a
process restart. Only the URL pointer and metadata are stored — the
media bytes themselves are always streamed on-demand from the
upstream CDN, never saved to disk.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StreamCache(Base):
    """A resolved upstream stream URL and its metadata."""

    __tablename__ = "stream_cache"

    # Bare provider media id, e.g. "H5dObFvq9VU".
    media_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    artist: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Wall-clock Unix timestamp (time.time()) when the URL expires.
    expires_at: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
