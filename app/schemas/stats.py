"""Pydantic models for stats."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class APIKeyStats(BaseModel):
    """Per-key usage statistics, returned by /stats (key-scoped) and /admin/stats."""

    key_id: Optional[int] = Field(
        default=None, description="Only present for admin views"
    )
    name: Optional[str] = Field(
        default=None, description="Only present for admin views"
    )
    tier: Optional[str] = None
    requests_today: int
    total_requests: int
    bytes_streamed: int
    daily_limit: int
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="0.0 to 1.0")


class GlobalStats(BaseModel):
    """System-wide aggregate stats, returned by /admin/stats only."""

    api_keys_total: int
    api_keys_active: int
    requests_today: int
    total_requests: int
    bytes_streamed: int
    cache_hit_rate: float
    provider_errors: int
    active_streams: int


class ErrorResponse(BaseModel):
    """Standard error response shape."""

    error: str
    detail: str
    request_id: Optional[str] = None
