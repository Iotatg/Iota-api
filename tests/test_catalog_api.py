"""Public catalog HTTP endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_search_returns_ranked_results(client):
    r = await client.get("/api/search", params={"q": "neon", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["results"][0]["video_id"] == "iotademo001"
    assert r.headers.get("X-Powered-By") == "Iota-Music-Engine"


@pytest.mark.asyncio
async def test_song_lookup_and_404(client):
    ok = await client.get("/api/song/iotademo001")
    assert ok.status_code == 200
    assert ok.json()["song"]["title"] == "Neon Drift"
    missing = await client.get("/api/song/doesnotexist")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_random_songs_and_stats(client):
    rnd = await client.get("/api/random", params={"limit": 2})
    assert rnd.status_code == 200
    assert rnd.json()["total_results"] == 2
    stats = await client.get("/api/stats")
    assert stats.status_code == 200
    assert stats.json()["total_songs"] == 2


@pytest.mark.asyncio
async def test_file_range_stream(client):
    full = await client.get("/api/file/iotademo001")
    assert full.status_code == 200
    assert full.headers.get("Accept-Ranges") == "bytes"
    size = int(full.headers["content-length"])
    partial = await client.get("/api/file/iotademo001", headers={"Range": "bytes=0-15"})
    assert partial.status_code == 206
    assert partial.headers["Content-Range"].startswith("bytes 0-15/")
    assert len(partial.content) == 16
    assert size > 16
