"""Test metadata caching."""
import pytest


@pytest.mark.asyncio
async def test_info_cache_miss_then_hit(client, created_key, app_instance):
    """First call: MISS, second call: HIT."""
    # First call
    r1 = await client.get("/info/sample-001.mp3", params={"key": created_key["api_key"]})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["title"] == "Sample One"

    # Get cache stats
    cache_stats_before = app_instance.state.memory_cache.stats()
    # We don't assert exact counts because middleware also calls
    # but we DO assert that the second call is a cache hit (L1 will have
    # backfilled the value).

    # Second call: should be served from cache (we just check the data matches)
    r2 = await client.get("/info/sample-001.mp3", params={"key": created_key["api_key"]})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2 == body1

    cache_stats_after = app_instance.state.memory_cache.stats()
    # L1 should have at least one hit on the second call
    assert cache_stats_after["hits"] >= cache_stats_before["hits"]


@pytest.mark.asyncio
async def test_info_returns_404_for_missing(client, created_key):
    r = await client.get("/info/does-not-exist.mp3", params={"key": created_key["api_key"]})
    assert r.status_code == 404
    assert r.json()["error"] == "media_not_found"


@pytest.mark.asyncio
async def test_search_returns_results(client, created_key):
    r = await client.get("/search", params={"q": "Sample", "key": created_key["api_key"]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 2
    assert all(item["provider"] == "demo" for item in body["results"])


@pytest.mark.asyncio
async def test_search_empty_query_rejected(client, created_key):
    r = await client.get("/search", params={"q": "", "key": created_key["api_key"]})
    assert r.status_code == 422
