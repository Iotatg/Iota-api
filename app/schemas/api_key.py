"""Pydantic models for API key management."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.api_key import APIKeyTier


class APIKeyCreateRequest(BaseModel):
    """Admin endpoint payload: create a new API key."""

    name: str = Field(..., min_length=1, max_length=128, description="Human-friendly name")
    tier: APIKeyTier = Field(default=APIKeyTier.FREE)
    daily_limit: Optional[int] = Field(default=None, ge=0, le=10_000_000, description="Daily request quota; 0 = unlimited")
    rate_per_minute: Optional[int] = Field(default=None, ge=0, le=1_000_000, description="Per-minute request limit; 0 = unlimited")
    concurrent_streams_limit: Optional[int] = Field(default=None, ge=0, le=1_000, description="Max concurrent streams; 0 = unlimited")
    expires_at: Optional[datetime] = None


class APIKeyCreateResponse(BaseModel):
    """Returned ONCE at creation. The plaintext key cannot be recovered later."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tier: APIKeyTier
    daily_limit: int
    rate_per_minute: int
    concurrent_streams_limit: int
    created_at: datetime
    expires_at: Optional[datetime]
    active: bool

    # Only present in the create response, never in subsequent reads.
    api_key: str = Field(..., description="Plaintext key. Store immediately — shown only once.")


class APIKeyView(BaseModel):
    """API key view WITHOUT the plaintext value (for list / get)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tier: APIKeyTier
    daily_limit: int
    rate_per_minute: int
    concurrent_streams_limit: int
    requests_today: int
    total_requests: int
    bytes_streamed: int
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    active: bool
