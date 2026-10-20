"""Search endpoint.

GET /search?q=...&limit=20
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import require_api_key
from app.cache.hierarchy import CacheResult
from app.config import get_settings
from app.database import get_session
from app.dependencies import get_cache, get_provider, get_rate_limiter
from app.models.api_key import APIKey
from app.schemas.media import MediaInfo, SearchResult
from app.services.media_provider import (
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.utils.logging import get_logger
from app.utils.metrics import provider_errors_total
from app.utils.rate_limit import RateLimiter

logger = get_logger(__name__)
router = APIRouter()


@router.get("/search", response_model=SearchResult)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> SearchResult:
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

    settings = get_settings()
    cache_key = f"search:{q.lower().strip()}:{limit}"

    # A search is answered from the cache when the same query ran before,
    # the provider is asked again only for a query that is not cached.
    lookup = await cache.get(cache_key)
    if lookup.result in (CacheResult.HIT_L1, CacheResult.HIT_L2):
        cached = lookup.value or {}
        return SearchResult(
            query=cached.get("query", q),
            count=cached.get("count", 0),
            results=[MediaInfo(**entry) for entry in cached.get("results", [])],
        )

    try:
        results = await provider.search(q, limit=limit)
    except ProviderUnavailableError as e:
        provider_errors_total.labels(provider=provider.name, kind="unavailable").inc()
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable",
            "detail": str(e),
        })
    except ProviderError as e:
        provider_errors_total.labels(provider=provider.name, kind="error").inc()
        raise HTTPException(status_code=502, detail={
            "error": "provider_error",
            "detail": str(e),
        })

    entries = [
        {
            "media_id": m.media_id,
            "title": m.title,
            "artist": m.artist,
            "duration_seconds": m.duration_seconds,
            "thumbnail_url": m.thumbnail_url,
            "size_bytes": m.size_bytes,
            "mime_type": m.mime_type,
            "provider": m.provider,
            "views": m.views,
            "likes": m.likes,
        }
        for m in results
    ]

    await cache.set(
        cache_key,
        {"query": q, "count": len(entries), "results": entries},
        ttl=settings.metadata_cache_ttl,
    )

    return SearchResult(
        query=q,
        count=len(entries),
        results=[MediaInfo(**entry) for entry in entries],
    )
