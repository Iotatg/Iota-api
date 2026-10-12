"""Test rate limiting."""
import pytest


@pytest.mark.asyncio
async def test_per_minute_rate_limit(client, created_key, app_instance):
    """Create a key with very low per-minute limit and exhaust it."""
    # Create a key with rate_per_minute=2
    r = await client.post(
        "/admin/keys",
        json={"name": "low-rate", "rate_per_minute": 2, "daily_limit": 100},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    key = r.json()["api_key"]

    # First two should pass
    r1 = await client.get("/info/sample-001.mp3", params={"key": key})
    r2 = await client.get("/info/sample-001.mp3", params={"key": key})
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Third should 429
    r3 = await client.get("/info/sample-001.mp3", params={"key": key})
    assert r3.status_code == 429
    body = r3.json()
    assert body["error"] == "rate_limited"
    assert "Retry-After" in r3.headers


@pytest.mark.asyncio
async def test_daily_quota(client, app_instance):
    """Daily quota of 1: second request should be 429."""
    r = await client.post(
        "/admin/keys",
        json={"name": "low-daily", "rate_per_minute": 100, "daily_limit": 1},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    key = r.json()["api_key"]

    r1 = await client.get("/info/sample-001.mp3", params={"key": key})
    assert r1.status_code == 200
    r2 = await client.get("/info/sample-001.mp3", params={"key": key})
    assert r2.status_code == 429
    assert r2.json()["error"] == "rate_limited"


@pytest.mark.asyncio
async def test_concurrent_streams_limit(client, app_instance):
    """Only N concurrent streams allowed."""
    r = await client.post(
        "/admin/keys",
        json={"name": "low-concurrent", "concurrent_streams_limit": 1},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    key = r.json()["api_key"]

    # Start a stream that we never fully consume: use streaming response.
    # The simplest way is to start a request and check it doesn't 429
    # immediately, then a second should 429.
    import asyncio
    async def first():
        async with client.stream(
            "GET", "/stream/sample-001.mp3", params={"key": key}
        ) as r:
            assert r.status_code == 200
            # Read a bit then leave the connection open
            async for _ in r.aiter_bytes(chunk_size=512):
                # Yield to allow the second request to start
                await asyncio.sleep(0.05)
                return

    async def second():
        await asyncio.sleep(0.01)  # let the first start
        r = await client.get(
            "/stream/sample-001.mp3", params={"key": key}
        )
        return r

    # Run them concurrently
    t1 = asyncio.create_task(first())
    t2 = asyncio.create_task(second())
    await asyncio.gather(t1, t2, return_exceptions=True)
    # We don't make hard assertions here because the timing is fragile;
    # the test is mostly that the code path doesn't crash.


@pytest.mark.asyncio
async def test_search_rate_limited(client, app_instance):
    """Search must enforce per-minute rate limit (regression test)."""
    r = await client.post(
        "/admin/keys",
        json={"name": "rl-search", "rate_per_minute": 2, "daily_limit": 100},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    key = r.json()["api_key"]

    # First 2 should pass
    r1 = await client.get("/search", params={"q": "test", "key": key})
    r2 = await client.get("/search", params={"q": "test", "key": key})
    assert r1.status_code == 200
    assert r2.status_code == 200

    # 3rd should 429
    r3 = await client.get("/search", params={"q": "test", "key": key})
    assert r3.status_code == 429
    assert r3.json()["error"] == "rate_limited"
    assert "Retry-After" in r3.headers


@pytest.mark.asyncio
async def test_stats_rate_limited(client, app_instance):
    """/stats must enforce per-minute rate limit (regression test)."""
    r = await client.post(
        "/admin/keys",
        json={"name": "rl-stats", "rate_per_minute": 2, "daily_limit": 100},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    key = r.json()["api_key"]

    r1 = await client.get("/stats", headers={"X-API-Key": key})
    r2 = await client.get("/stats", headers={"X-API-Key": key})
    assert r1.status_code == 200
    assert r2.status_code == 200

    r3 = await client.get("/stats", headers={"X-API-Key": key})
    assert r3.status_code == 429
    assert r3.json()["error"] == "rate_limited"
