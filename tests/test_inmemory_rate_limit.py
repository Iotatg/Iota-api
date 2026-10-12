"""Tests for the in-memory rate limiter fallback."""
import os
import importlib

import pytest


@pytest.fixture
def inmemory_rl(monkeypatch):
    monkeypatch.setenv("REDIS_DISABLED", "true")
    import app.utils.rate_limit as rl_module
    importlib.reload(rl_module)
    return rl_module


@pytest.mark.asyncio
async def test_inmemory_rate_limiter_minute(inmemory_rl):
    lim = inmemory_rl.InMemoryRateLimiter()
    for i in range(3):
        r = await lim.check_minute(key_id=999, limit=3)
        assert r.allowed, f"req {i} should be allowed"
    r = await lim.check_minute(key_id=999, limit=3)
    assert not r.allowed
    assert r.reason == "per-minute rate limit exceeded"


@pytest.mark.asyncio
async def test_inmemory_rate_limiter_day(inmemory_rl):
    lim = inmemory_rl.InMemoryRateLimiter()
    for i in range(2):
        r = await lim.check_day(key_id=1000, limit=2)
        assert r.allowed
    r = await lim.check_day(key_id=1000, limit=2)
    assert not r.allowed
    assert r.reason == "daily quota exceeded"


@pytest.mark.asyncio
async def test_inmemory_concurrent_streams(inmemory_rl):
    lim = inmemory_rl.InMemoryRateLimiter()
    t1 = await lim.acquire_stream(key_id=1001, limit=2)
    t2 = await lim.acquire_stream(key_id=1001, limit=2)
    t3 = await lim.acquire_stream(key_id=1001, limit=2)
    assert t1 and t2
    assert t3 is None, "third should be denied"
    await lim.release_stream(key_id=1001, token=t1)
    t4 = await lim.acquire_stream(key_id=1001, limit=2)
    assert t4 is not None, "after release, new acquire should succeed"


def test_unified_uses_memory_when_disabled(monkeypatch):
    monkeypatch.setenv("REDIS_DISABLED", "true")
    import app.utils.rate_limit as rl_module
    importlib.reload(rl_module)
    rl = rl_module.RateLimiter(redis_client=None)
    assert rl._backend == "memory"
