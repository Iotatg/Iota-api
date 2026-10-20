"""APIKey ORM model.

Only the SHA-256 hash of the key is stored. The plaintext key is shown to the
user exactly once at creation time and cannot be recovered.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class APIKeyTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    UNLIMITED = "unlimited"


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # SHA-256 hex digest of the plaintext key. 64 chars, indexed for lookup.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    tier: Mapped[APIKeyTier] = mapped_column(
        Enum(APIKeyTier, name="api_key_tier"),
        nullable=False,
        default=APIKeyTier.FREE,
    )

    # Limits
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10_000)
    rate_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    concurrent_streams_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )

    # Counters (denormalized for fast reads; reset at midnight UTC for daily_*)
    requests_today: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    requests_today_date: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # "YYYY-MM-DD" — when daily counter was last reset
    total_requests: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_streamed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_api_keys_active_expires", "active", "expires_at"),
    )

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        now = now or datetime.now(timezone.utc)
        expires_at = self.expires_at
        # The column is timezone aware, but a value that was stored as a naive
        # datetime comes back without an offset. Both sides are normalised to
        # UTC so the comparison never raises.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now >= expires_at

    def is_usable(self, now: Optional[datetime] = None) -> bool:
        return self.active and not self.is_expired(now)

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name!r} tier={self.tier.value} active={self.active}>"
