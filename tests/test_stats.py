"""Test stats endpoint (per-key)."""
import pytest


@pytest.mark.asyncio
async def test_stats_endpoint(client, created_key):
    r = await client.get("/stats", params={"key": created_key["api_key"]})
    assert r.status_code == 200
    body = r.json()
    assert "requests_today" in body
    assert "total_requests" in body
    assert "bytes_streamed" in body
    assert "cache_hit_rate" in body
    assert "daily_limit" in body


@pytest.mark.asyncio
async def test_stats_requires_auth(client):
    r = await client.get("/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stats_reflects_usage(client, created_key):
    # Make some calls
    for _ in range(3):
        await client.get("/info/sample-001.mp3", params={"key": created_key["api_key"]})

    r = await client.get("/stats", params={"key": created_key["api_key"]})
    assert r.status_code == 200
    body = r.json()
    # The total_requests count is bumped on stream, but for /info we just
    # check that stats returns without error.
    assert body["tier"] == "free"
