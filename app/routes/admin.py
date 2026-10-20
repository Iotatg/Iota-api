"""Admin endpoints. Protected by X-Admin-Token header.

POST   /admin/keys         — create a new API key
GET    /admin/keys         — list API keys (no plaintext)
GET    /admin/keys/{id}    — single key (no plaintext)
DELETE /admin/keys/{id}    — disable a key
GET    /admin/stats        — system-wide stats
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.admin import require_admin
from app.config import generate_api_key, get_settings, hash_api_key
from app.database import get_session
from app.models.api_key import APIKey, APIKeyTier
from app.schemas.api_key import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyView
from app.schemas.stats import APIKeyStats, GlobalStats
from app.utils.logging import get_logger
from app.utils.metrics import active_stream_count, cache_hit_rate, sample_sum

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/admin/keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_key(
    payload: APIKeyCreateRequest,
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> APIKeyCreateResponse:
    settings = get_settings()
    plaintext = generate_api_key(settings.api_key_prefix, settings.api_key_bytes)
    key_hash = hash_api_key(plaintext)

    api_key = APIKey(
        name=payload.name,
        key_hash=key_hash,
        tier=payload.tier,
        daily_limit=payload.daily_limit if payload.daily_limit is not None else settings.default_daily_limit,
        rate_per_minute=payload.rate_per_minute if payload.rate_per_minute is not None else settings.default_rate_per_minute,
        concurrent_streams_limit=payload.concurrent_streams_limit
        if payload.concurrent_streams_limit is not None
        else settings.default_concurrent_streams,
        expires_at=payload.expires_at,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    logger.info("admin_key_created", extra={"key_id": api_key.id, "key_name": api_key.name})
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        tier=api_key.tier,
        daily_limit=api_key.daily_limit,
        rate_per_minute=api_key.rate_per_minute,
        concurrent_streams_limit=api_key.concurrent_streams_limit,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        active=api_key.active,
        api_key=plaintext,
    )


@router.get("/admin/keys", response_model=List[APIKeyView])
async def list_keys(
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> List[APIKeyView]:
    result = await session.execute(
        select(APIKey).order_by(APIKey.id.desc())
    )
    keys = result.scalars().all()
    return [APIKeyView.model_validate(k) for k in keys]


@router.get("/admin/keys/{key_id}", response_model=APIKeyView)
async def get_key(
    key_id: int,
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> APIKeyView:
    api_key = await session.get(APIKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail={
            "error": "key_not_found",
            "detail": f"No key with id {key_id}.",
        })
    return APIKeyView.model_validate(api_key)


@router.delete("/admin/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_key(
    key_id: int,
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> Response:
    api_key = await session.get(APIKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail={
            "error": "key_not_found",
            "detail": f"No key with id {key_id}.",
        })
    # We soft-delete: keep the row for audit, mark inactive.
    api_key.active = False
    await session.commit()
    logger.info("admin_key_disabled", extra={"key_id": api_key.id, "key_name": api_key.name})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/stats", response_model=GlobalStats)
async def global_stats(
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> GlobalStats:
    total_keys = await session.scalar(select(func.count(APIKey.id)))
    active_keys = await session.scalar(
        select(func.count(APIKey.id)).where(APIKey.active.is_(True))
    )
    requests_today = await session.scalar(
        select(func.coalesce(func.sum(APIKey.requests_today), 0))
    )
    total_requests = await session.scalar(
        select(func.coalesce(func.sum(APIKey.total_requests), 0))
    )
    bytes_streamed = await session.scalar(
        select(func.coalesce(func.sum(APIKey.bytes_streamed), 0))
    )
    return GlobalStats(
        api_keys_total=int(total_keys or 0),
        api_keys_active=int(active_keys or 0),
        requests_today=int(requests_today or 0),
        total_requests=int(total_requests or 0),
        bytes_streamed=int(bytes_streamed or 0),
        cache_hit_rate=round(cache_hit_rate(), 4),
        provider_errors=int(sample_sum("provider_errors_total")),
        active_streams=active_stream_count(),
    )
