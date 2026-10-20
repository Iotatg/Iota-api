"""Health and root endpoints.

GET /        — service identity (cheap, no auth)
GET /health  — deep health check (Postgres, Redis)
GET /metrics — Prometheus
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_redis_cache
from app.utils.logging import get_logger
from app.utils.metrics import render_metrics

logger = get_logger(__name__)
router = APIRouter()


@router.get("/identity", include_in_schema=False)
async def identity() -> dict:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
async def health(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis_cache=Depends(get_redis_cache),
) -> dict:
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.error("health_postgres_error", extra={"err": str(e)})
        checks["postgres"] = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    if redis_cache is not None:
        try:
            if await redis_cache.ping():
                checks["redis"] = "ok"
            else:
                checks["redis"] = "error"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        except Exception as e:
            logger.error("health_redis_error", extra={"err": str(e)})
            checks["redis"] = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        checks["redis"] = "disabled"

    overall = "ok" if all(v in ("ok", "disabled") for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "service": settings.app_name,
        "env": settings.app_env.value,
        "checks": checks,
    }


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
