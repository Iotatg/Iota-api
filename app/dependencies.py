"""Shared FastAPI dependencies.

Objects are created at app startup (see app/main.py lifespan) and stored on
`app.state`. These functions retrieve them lazily so that tests can override
them via `app.dependency_overrides[...]`.
"""
from __future__ import annotations

from fastapi import Request

from app.cache.hierarchy import CacheHierarchy
from app.cache.memory_cache import MemoryCache
from app.cache.redis_cache import RedisCache
from app.services.media_provider import MediaProvider
from app.services.storage import StorageService
from app.services.stream_proxy import StreamProxy
from app.utils.rate_limit import RateLimiter


def get_memory_cache(request: Request) -> MemoryCache:
    return request.app.state.memory_cache


def get_redis_cache(request: Request) -> "RedisCache | None":
    return request.app.state.redis_cache


def get_cache(request: Request) -> CacheHierarchy:
    return request.app.state.cache


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_storage(request: Request) -> StorageService:
    return request.app.state.storage


def get_provider(request: Request) -> MediaProvider:
    return request.app.state.provider


def get_stream_proxy(request: Request) -> StreamProxy:
    return request.app.state.stream_proxy

