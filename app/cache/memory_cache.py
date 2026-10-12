"""L1 in-memory cache for media metadata.

Thread-safe LRU with a max size. Used as the fastest layer of the cache
hierarchy. We use a simple OrderedDict rather than functools.lru_cache
because we want to expose cache stats (hits / misses / size).
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class MemoryCache(Generic[T]):
    def __init__(self, max_size: int = 10_000, default_ttl: int = 300) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._data: "OrderedDict[str, CacheEntry[T]]" = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at < time.time():
                self._data.pop(key, None)
                self.misses += 1
                return None
            # Mark as recently used
            self._data.move_to_end(key)
            self.hits += 1
            return entry.value

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        with self._lock:
            ttl = ttl or self._default_ttl
            self._data[key] = CacheEntry(value=value, expires_at=time.time() + ttl)
            self._data.move_to_end(key)
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)
                self.evictions += 1

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            return {
                "size": len(self._data),
                "max_size": self._max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": (self.hits / total) if total else 0.0,
            }
