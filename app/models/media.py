"""Media metadata ORM model.

We persist media metadata that has been resolved at least once, so that we
have a record for analytics and so that /info doesn't re-call the provider
on every request. Audio bytes themselves live in the storage layer (local
filesystem or S3), keyed by storage_key.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Stable identifier returned by the provider (e.g. "demo-001" or a real ID).
    media_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Where the actual audio bytes are stored
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="audio/mpeg")

    # Provider that produced this metadata (e.g. "demo", "spotify", "jamendo")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="demo")

    # Optional raw metadata JSON for forward-compat (artist, album, year, etc.)
    extra_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_media_provider_media_id", "provider", "media_id"),
    )

    def __repr__(self) -> str:
        return f"<Media id={self.id} media_id={self.media_id!r} provider={self.provider}>"
