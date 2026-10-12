"""Media info endpoint.

GET /info/{media_id}

Returns metadata for a media_id. The metadata is cached in L1+L2.
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import require_api_key
from app.cache.hierarchy import CacheResult
from app.config import get_settings
from app.database import get_session
from app.dependencies import get_cache, get_provider, get_rate_limiter
from app.models.api_key import APIKey
from app.schemas.media import MediaInfo, StreamInfo
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.utils.logging import get_logger
from app.utils.metrics import provider_errors_total
from app.utils.rate_limit import RateLimiter

logger = get_logger(__name__)
router = APIRouter()


async def _check_rate_limit(
    api_key: APIKey, rate_limiter: RateLimiter
) -> None:
    rl = await rate_limiter.check(api_key.id, api_key.rate_per_minute, api_key.daily_limit)
    if not rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "detail": rl.reason},
            headers={
                "Retry-After": str(rl.retry_after_seconds),
                "X-RateLimit-Remaining-Minute": str(max(0, rl.remaining_minute)),
                "X-RateLimit-Remaining-Day": str(max(0, rl.remaining_day)),
            },
        )


@router.get("/info/{media_id}", response_model=MediaInfo)
async def info(
    request: Request,
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> MediaInfo:
    await _check_rate_limit(api_key, rate_limiter)
    settings = get_settings()
    cache_key = f"info:{media_id}"

    # Try cache first
    lookup = await cache.get(cache_key)
    if lookup.result in (CacheResult.HIT_L1, CacheResult.HIT_L2):
        return MediaInfo(**lookup.value)

    # Cache miss → call provider
    try:
        meta = await provider.get_info(media_id)
    except MediaNotFoundError:
        provider_errors_total.labels(provider=provider.name, kind="not_found").inc()
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": f"No media with id {media_id!r}.",
        })
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

    payload = {
        "media_id": meta.media_id,
        "title": meta.title,
        "artist": meta.artist,
        "duration_seconds": meta.duration_seconds,
        "thumbnail_url": meta.thumbnail_url,
        "size_bytes": meta.size_bytes,
        "mime_type": meta.mime_type,
        "provider": meta.provider,
        "views": meta.views,
        "likes": meta.likes,
    }
    await cache.set(cache_key, payload, ttl=settings.metadata_cache_ttl)
    return MediaInfo(**payload)


@router.get("/stream-info/{media_id}", response_model=StreamInfo)
async def stream_info(
    request: Request,
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> StreamInfo:
    """Convenience endpoint: same as /info but also includes a stream URL."""
    await _check_rate_limit(api_key, rate_limiter)
    info_obj = await info(request, media_id, api_key, session, cache, provider, rate_limiter)
    return StreamInfo(
        media_id=info_obj.media_id,
        title=info_obj.title,
        artist=info_obj.artist,
        duration_seconds=info_obj.duration_seconds,
        size_bytes=info_obj.size_bytes,
        mime_type=info_obj.mime_type,
        stream_url=f"/stream/{info_obj.media_id}",
        supports_range=True,
    )
