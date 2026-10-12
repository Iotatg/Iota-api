"""Rate limiting with optional in-memory fallback.

When REDIS_DISABLED=true the rate limiter uses per-process dicts instead of
Redis. This is intended for free-tier deployments where the additional
Redis service would exceed the resource budget. Trade-offs:

  - Limits are per-replica, not global. With one replica (default) this
    is fine; with multiple replicas each enforces its own quota.
  - State is lost on restart. New instance starts with clean counters.
  - Concurrent stream counter is per-process, so total concurrent streams
    is bounded by N_replicas * concurrent_streams_limit.

For production deployments leave REDIS_DISABLED unset so all replicas
share Redis state.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger
from app.utils.metrics import REGISTRY  # noqa: F401  (kept for future gauges)

logger = get_logger(__name__)

REDIS_DISABLED = os.getenv("REDIS_DISABLED", "false").lower() in ("1", "true", "yes")


@dataclass
class RateLimitResult:
    allowed: bool
    remaining_minute: int
    remaining_day: int
    retry_after_seconds: int
    reason: str = ""


class InMemoryRateLimiter:
    """Per-process rate limiter. No external dependency."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._minute_buckets: dict[tuple[int, int], int] = defaultdict(int)
        self._day_buckets: dict[tuple[int, str], int] = defaultdict(int)
        self._streams: dict[int, set[str]] = defaultdict(set)
        # cleanup of old minute buckets
        self._last_minute_seen: int = 0

    async def check_minute(self, key_id: int, limit: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(
                allowed=True,
                remaining_minute=-1,
                remaining_day=-1,
                retry_after_seconds=0,
                reason="unlimited",
            )
        bucket = int(time.time()) // self.settings.rate_limit_window_seconds
        self._last_minute_seen = max(self._last_minute_seen, bucket)
        k = (key_id, bucket)
        self._minute_buckets[k] += 1
        count = self._minute_buckets[k]
        # opportunistically evict old buckets
        if len(self._minute_buckets) > 1024:
            cutoff = bucket - 5
            for old_k in list(self._minute_buckets.keys()):
                if old_k[1] < cutoff:
                    self._minute_buckets.pop(old_k, None)
        if count > limit:
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_day=-1,
                retry_after_seconds=self.settings.rate_limit_window_seconds,
                reason="per-minute rate limit exceeded",
            )
        return RateLimitResult(
            allowed=True,
            remaining_minute=max(0, limit - count),
            remaining_day=-1,
            retry_after_seconds=0,
        )

    async def check_day(self, key_id: int, limit: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(
                allowed=True,
                remaining_minute=-1,
                remaining_day=-1,
                retry_after_seconds=0,
                reason="unlimited",
            )
        day = time.strftime("%Y-%m-%d", time.gmtime())
        k = (key_id, day)
        self._day_buckets[k] += 1
        count = self._day_buckets[k]
        if count > limit:
            now = time.gmtime()
            retry = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
            return RateLimitResult(
                allowed=False,
                remaining_minute=-1,
                remaining_day=0,
                retry_after_seconds=retry,
                reason="daily quota exceeded",
            )
        return RateLimitResult(
            allowed=True,
            remaining_minute=-1,
            remaining_day=max(0, limit - count),
            retry_after_seconds=0,
        )

    async def check(
        self, key_id: int, per_minute: int, daily: int
    ) -> RateLimitResult:
        m = await self.check_minute(key_id, per_minute)
        if not m.allowed:
            return m
        d = await self.check_day(key_id, daily)
        if not d.allowed:
            return d
        return RateLimitResult(
            allowed=True,
            remaining_minute=m.remaining_minute,
            remaining_day=d.remaining_day,
            retry_after_seconds=0,
        )

    async def acquire_stream(self, key_id: int, limit: int) -> Optional[str]:
        if limit <= 0:
            return f"{time.time_ns()}-{id(object())}"
        token = f"{time.time_ns()}-{id(object())}"
        active = self._streams[key_id]
        if len(active) >= limit:
            return None
        active.add(token)
        return token

    async def release_stream(self, key_id: int, token: str) -> None:
        self._streams[key_id].discard(token)

    async def active_streams_count(self, key_id: int) -> int:
        return len(self._streams[key_id])


# Try to import redis. If unavailable, force fallback.
try:
    import redis.asyncio as redis  # noqa: F401

    HAS_REDIS_LIB = True
except ImportError:  # pragma: no cover
    HAS_REDIS_LIB = False
    REDIS_DISABLED = True


class RateLimiter:
    """Unified rate limiter.

    Uses Redis when REDIS_DISABLED is false and a Redis client is reachable.
    Otherwise falls back to per-process in-memory counters.
    """

    def __init__(self, redis_client=None) -> None:
        self.settings = get_settings()
        self._fallback = InMemoryRateLimiter()
        self._r = None
        if REDIS_DISABLED or redis_client is None or not HAS_REDIS_LIB:
            if REDIS_DISABLED:
                logger.info("rate_limiter_using_inmemory", extra={"reason": "REDIS_DISABLED=true"})
            self._backend = "memory"
            return
        self._r = redis_client
        self._backend = "redis"

    async def check(self, key_id: int, per_minute: int, daily: int) -> RateLimitResult:
        if self._backend == "memory":
            return await self._fallback.check(key_id, per_minute, daily)
        return await self._redis_check(key_id, per_minute, daily)

    async def check_minute(self, key_id: int, limit: int) -> RateLimitResult:
        if self._backend == "memory":
            return await self._fallback.check_minute(key_id, limit)
        return await self._redis_check_minute(key_id, limit)

    async def check_day(self, key_id: int, limit: int) -> RateLimitResult:
        if self._backend == "memory":
            return await self._fallback.check_day(key_id, limit)
        return await self._redis_check_day(key_id, limit)

    async def acquire_stream(self, key_id: int, limit: int) -> Optional[str]:
        if self._backend == "memory":
            return await self._fallback.acquire_stream(key_id, limit)
        return await self._redis_acquire_stream(key_id, limit)

    async def release_stream(self, key_id: int, token: str) -> None:
        if self._backend == "memory":
            await self._fallback.release_stream(key_id, token)
            return
        await self._redis_release_stream(key_id, token)

    async def active_streams_count(self, key_id: int) -> int:
        if self._backend == "memory":
            return await self._fallback.active_streams_count(key_id)
        return await self._redis_active_streams_count(key_id)

    # ── Redis backend (delegated) ───────────────────────────────────────
    async def _redis_check(self, key_id, per_minute, daily):
        m = await self._redis_check_minute(key_id, per_minute)
        if not m.allowed:
            return m
        d = await self._redis_check_day(key_id, daily)
        if not d.allowed:
            return d
        return RateLimitResult(
            allowed=True,
            remaining_minute=m.remaining_minute,
            remaining_day=d.remaining_day,
            retry_after_seconds=0,
        )

    async def _redis_check_minute(self, key_id, limit):
        if limit <= 0:
            return RateLimitResult(
                allowed=True, remaining_minute=-1, remaining_day=-1,
                retry_after_seconds=0, reason="unlimited",
            )
        import redis.asyncio as redis
        bucket = int(time.time()) // self.settings.rate_limit_window_seconds
        key = f"rl:{key_id}:m:{bucket}"
        try:
            count = await self._r.incr(key)
            if count == 1:
                await self._r.expire(key, self.settings.rate_limit_window_seconds * 2)
        except redis.RedisError as e:
            logger.error("redis_error", extra={"op": "check_minute", "err": str(e)})
            return RateLimitResult(
                allowed=False, remaining_minute=0, remaining_day=0,
                retry_after_seconds=60, reason="rate-limit backend unavailable",
            )
        if count > limit:
            return RateLimitResult(
                allowed=False, remaining_minute=0, remaining_day=-1,
                retry_after_seconds=self.settings.rate_limit_window_seconds,
                reason="per-minute rate limit exceeded",
            )
        return RateLimitResult(
            allowed=True, remaining_minute=max(0, limit - count),
            remaining_day=-1, retry_after_seconds=0,
        )

    async def _redis_check_day(self, key_id, limit):
        if limit <= 0:
            return RateLimitResult(
                allowed=True, remaining_minute=-1, remaining_day=-1,
                retry_after_seconds=0, reason="unlimited",
            )
        import redis.asyncio as redis
        day = time.strftime("%Y-%m-%d", time.gmtime())
        key = f"rl:{key_id}:d:{day}"
        try:
            count = await self._r.incr(key)
            if count == 1:
                await self._r.expire(key, 90000)
        except redis.RedisError as e:
            logger.error("redis_error", extra={"op": "check_day", "err": str(e)})
            return RateLimitResult(
                allowed=False, remaining_minute=-1, remaining_day=0,
                retry_after_seconds=60, reason="rate-limit backend unavailable",
            )
        if count > limit:
            now = time.gmtime()
            retry = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
            return RateLimitResult(
                allowed=False, remaining_minute=-1, remaining_day=0,
                retry_after_seconds=retry, reason="daily quota exceeded",
            )
        return RateLimitResult(
            allowed=True, remaining_minute=-1,
            remaining_day=max(0, limit - count), retry_after_seconds=0,
        )

    async def _redis_acquire_stream(self, key_id, limit):
        if limit <= 0:
            return f"{time.time_ns()}-{id(object())}"
        import redis.asyncio as redis
        token = f"{time.time_ns()}-{id(object())}"
        key = f"streams:{key_id}"
        try:
            current = await self._r.incr(key)
            if current > limit:
                await self._r.decr(key)
                return None
            return token
        except redis.RedisError as e:
            logger.error("redis_error", extra={"op": "acquire_stream", "err": str(e)})
            return None

    async def _redis_release_stream(self, key_id, token):
        import redis.asyncio as redis
        key = f"streams:{key_id}"
        try:
            await self._r.decr(key)
        except redis.RedisError as e:
            logger.error("redis_error", extra={"op": "release_stream", "err": str(e)})

    async def _redis_active_streams_count(self, key_id):
        import redis.asyncio as redis
        try:
            v = await self._r.get(f"streams:{key_id}")
            return int(v) if v else 0
        except redis.RedisError:
            return 0
