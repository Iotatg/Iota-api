"""Stats endpoint (per-key)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import require_api_key
from app.database import get_session
from app.dependencies import get_memory_cache, get_rate_limiter
from app.models.api_key import APIKey
from app.schemas.stats import APIKeyStats
from app.utils.rate_limit import RateLimiter

router = APIRouter()


@router.get("/stats", response_model=APIKeyStats)
async def my_stats(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    mem_cache=Depends(get_memory_cache),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> APIKeyStats:
    rl = await rate_limiter.check(api_key.id, api_key.rate_per_minute, api_key.daily_limit)
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": rl.reason,
                "retry_after_seconds": rl.retry_after_seconds,
                "limit_type": "per_minute" if rl.remaining_minute == 0 else "daily",
            },
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )
    cache_stats = mem_cache.stats()
    return APIKeyStats(
        key_id=api_key.id,
        name=api_key.name,
        tier=api_key.tier.value,
        requests_today=api_key.requests_today,
        total_requests=api_key.total_requests,
        bytes_streamed=api_key.bytes_streamed,
        daily_limit=api_key.daily_limit,
        cache_hit_rate=cache_stats.get("hit_rate", 0.0),
    )
