"""Two-level cache hierarchy (L1 in-memory + L2 Redis) for media metadata.

When looking up an entry:
1. Try L1. If hit, return.
2. Try L2. If hit, populate L1 and return.
3. Miss: caller resolves from upstream and calls `set`.

L3 (storage / object store) is NOT part of the cache hierarchy because it
serves bytes, not metadata.

If `l2` is None (e.g. REDIS_DISABLED=true), the hierarchy falls back to L1
only. All writes go to L1 with the configured TTL.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.cache.memory_cache import MemoryCache
from app.cache.redis_cache import RedisCache
from app.utils.metrics import cache_hits_total, cache_misses_total


class CacheResult(str, Enum):
    HIT_L1 = "HIT_L1"
    HIT_L2 = "HIT_L2"
    MISS = "MISS"
    STALE = "STALE"


@dataclass
class CacheLookup:
    result: CacheResult
    value: Optional[Any] = None


class CacheHierarchy:
    def __init__(self, l1: MemoryCache, l2: Optional[RedisCache] = None, l1_ttl: int = 60) -> None:
        self.l1 = l1
        self.l2 = l2
        self.l1_ttl = l1_ttl  # L1 TTL is shorter than L2 because it's per-process

    async def get(self, key: str) -> CacheLookup:
        v = self.l1.get(key)
        if v is not None:
            cache_hits_total.labels(level="l1").inc()
            return CacheLookup(CacheResult.HIT_L1, v)
        cache_misses_total.labels(level="l1").inc()

        if self.l2 is None:
            return CacheLookup(CacheResult.MISS, None)
        v = await self.l2.get(key)
        if v is not None:
            cache_hits_total.labels(level="l2").inc()
            # Backfill L1 with a short TTL
            self.l1.set(key, v, ttl=self.l1_ttl)
            return CacheLookup(CacheResult.HIT_L2, v)
        cache_misses_total.labels(level="l2").inc()
        return CacheLookup(CacheResult.MISS, None)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if self.l2 is not None:
            # Always write to L2 (canonical); L1 backfill is on read
            await self.l2.set(key, value, ttl=ttl)
        self.l1.set(key, value, ttl=min(self.l1_ttl, ttl) if ttl else self.l1_ttl)

    async def delete(self, key: str) -> None:
        self.l1.delete(key)
        if self.l2 is not None:
            await self.l2.delete(key)
