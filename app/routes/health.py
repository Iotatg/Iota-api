"""Health, readiness and root endpoints.

GET /             — service identity (cheap, no auth)
GET /health/live  — liveness probe: the process is up. Touches no
                    dependency, so it stays fast even when the database
                    or Redis is saturated.
GET /health/ready — readiness probe: the dependencies are reachable.
GET /health       — deep check, served from the readiness cache.
GET /metrics      — Prometheus
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.admin import check_admin_token
from app.database import get_session
from app.dependencies import get_redis_cache
from app.utils.logging import get_logger
from app.utils.metrics import render_metrics

logger = get_logger(__name__)
router = APIRouter()

# The dependency check is cached for a few seconds. A health endpoint
# that queries the database on every call becomes the slowest endpoint
# in the service and drains the connection pool under a probe storm.
_check_cache: dict = {"at": 0.0, "payload": None}


async def _collect_checks(session: AsyncSession, redis_cache) -> tuple[dict, str]:
    checks: dict[str, str] = {}
    worst = "ok"

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.error("health_postgres_error", extra={"err": str(e)})
        checks["postgres"] = "error"
        worst = "degraded"

    if redis_cache is not None:
        try:
            if await redis_cache.ping():
                checks["redis"] = "ok"
            else:
                checks["redis"] = "error"
                worst = "degraded"
        except Exception as e:
            logger.error("health_redis_error", extra={"err": str(e)})
            checks["redis"] = "error"
            worst = "degraded"
    else:
        checks["redis"] = "disabled"

    return checks, worst


async def _cached_checks(session: AsyncSession, redis_cache) -> tuple[dict, str]:
    ttl = max(0.0, float(get_settings().health_check_cache_ttl))
    now = time.monotonic()
    payload = _check_cache["payload"]
    if payload is not None and now - _check_cache["at"] < ttl:
        return payload
    checks, worst = await _collect_checks(session, redis_cache)
    _check_cache["at"] = now
    _check_cache["payload"] = (checks, worst)
    return checks, worst


@router.get("/identity", include_in_schema=False)
async def identity() -> dict:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "liveness": "/health/live",
        "readiness": "/health/ready",
    }


@router.get("/health/live", include_in_schema=False)
async def health_live() -> dict:
    """Liveness probe. No dependency is touched, so this answers in
    microseconds even when everything else is saturated."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env.value,
    }


@router.get("/health/ready", include_in_schema=False)
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis_cache=Depends(get_redis_cache),
) -> dict:
    """Readiness probe: the dependencies are reachable.

    A load balancer must not route traffic here while the database is
    down, so this reports 503 in that case."""
    settings = get_settings()
    checks, overall = await _cached_checks(session, redis_cache)
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": overall,
        "service": settings.app_name,
        "env": settings.app_env.value,
        "checks": checks,
    }


@router.get("/health")
async def health(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis_cache=Depends(get_redis_cache),
) -> dict:
    settings = get_settings()
    checks, overall = await _cached_checks(session, redis_cache)
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": overall,
        "service": settings.app_name,
        "env": settings.app_env.value,
        "checks": checks,
    }


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    """Prometheus metrics.

    Metrics expose request rates, latency and endpoint usage, which is
    useful reconnaissance. The endpoint therefore requires the admin
    token unless it is explicitly opened up for the scraper.
    """
    settings = get_settings()
    if settings.metrics_require_admin_token:
        check_admin_token(request.headers.get("X-Admin-Token"))
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
