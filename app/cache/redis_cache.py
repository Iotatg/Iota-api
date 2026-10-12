"""L2 Redis cache for media metadata.

Stores JSON-serialized values with a TTL. Used for cross-instance cache
sharing and to survive process restarts.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Thin wrapper over redis.asyncio for JSON-serialised values."""

    PREFIX = "meta:"

    def __init__(self, client: "redis.Redis", default_ttl: int = 300) -> None:
        self.r = client
        self.default_ttl = default_ttl
        self._settings = get_settings()

    def _k(self, key: str) -> str:
        return f"{self.PREFIX}{key}"

    async def get(self, key: str) -> Optional[Any]:
        try:
            raw = await self.r.get(self._k(key))
        except redis.RedisError as e:
            logger.error("redis_get_error", extra={"key": key, "err": str(e)})
            return None
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        payload = json.dumps(value, default=str)
        try:
            await self.r.set(self._k(key), payload, ex=ttl)
        except redis.RedisError as e:
            logger.error("redis_set_error", extra={"key": key, "err": str(e)})

    async def delete(self, key: str) -> None:
        try:
            await self.r.delete(self._k(key))
        except redis.RedisError as e:
            logger.error("redis_del_error", extra={"key": key, "err": str(e)})

    async def incr(self, key: str, ttl: Optional[int] = None) -> Optional[int]:
        full = self._k(key)
        try:
            v = await self.r.incr(full)
            if v == 1 and ttl:
                await self.r.expire(full, ttl)
            return int(v)
        except redis.RedisError as e:
            logger.error("redis_incr_error", extra={"key": key, "err": str(e)})
            return None

    async def ping(self) -> bool:
        try:
            return bool(await self.r.ping())
        except redis.RedisError:
            return False
