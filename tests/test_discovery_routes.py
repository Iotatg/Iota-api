"""Route tests for /lyrics/{id} and /similar/{id}."""
import pytest

from app.services.discovery import (
    DiscoveryClient,
    DiscoveryNotFoundError,
    DiscoveryUnavailableError,
)


@pytest.mark.asyncio
async def test_lyrics_route_ok(client, created_key, monkeypatch):
    async def fake(self, title, artist=None, album=None, duration_seconds=None):
        assert title == "Sample One"
        return {"title": title, "artist": artist, "synced": "[00:01.00] la",
                "plain": "la", "source": "lrclib"}
    monkeypatch.setattr(DiscoveryClient, "lyrics", fake)
    r = await client.get(
        "/lyrics/sample-001.mp3", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["synced"].startswith("[00:01")
    assert body["media_id"] == "sample-001.mp3"


@pytest.mark.asyncio
async def test_lyrics_route_not_found(client, created_key, monkeypatch):
    async def fake(self, *a, **k):
        raise DiscoveryNotFoundError("nope")
    monkeypatch.setattr(DiscoveryClient, "lyrics", fake)
    r = await client.get(
        "/lyrics/sample-001.mp3", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 404
    assert r.json()["error"] == "lyrics_not_found"


@pytest.mark.asyncio
async def test_lyrics_route_upstream_error(client, created_key, monkeypatch):
    async def fake(self, *a, **k):
        raise DiscoveryUnavailableError("lrclib down")
    monkeypatch.setattr(DiscoveryClient, "lyrics", fake)
    r = await client.get(
        "/lyrics/sample-001.mp3", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_lyrics_route_unknown_media(client, created_key):
    r = await client.get(
        "/lyrics/nope:123", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 404
    assert r.json()["error"] == "media_not_found"


@pytest.mark.asyncio
async def test_similar_route_ok(client, created_key, monkeypatch):
    async def fake(self, title, artist=None, limit=10, deezer_id=None):
        assert deezer_id is None  # demo track is not deezer-native
        return [{"media_id": "dz:1", "provider": "dz", "title": "X",
                 "artist": "Y", "duration_seconds": 100, "thumbnail_url": None}]
    monkeypatch.setattr(DiscoveryClient, "similar", fake)
    r = await client.get(
        "/similar/sample-001.mp3", params={"key": created_key["api_key"], "limit": 5}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["media_id"] == "dz:1"


@pytest.mark.asyncio
async def test_similar_route_passes_native_deezer_id(
    client, created_key, monkeypatch
):
    seen = {}

    async def fake(self, title, artist=None, limit=10, deezer_id=None):
        seen["deezer_id"] = deezer_id
        return [{"media_id": "dz:9", "provider": "dz", "title": "Z",
                 "artist": None, "duration_seconds": None, "thumbnail_url": None}]
    monkeypatch.setattr(DiscoveryClient, "similar", fake)

    # register dz demo metadata via a fake provider on the registry
    async def fake_info(self, media_id):
        from app.services.media_provider import MediaMetadata
        return MediaMetadata(
            media_id="dz:555", title="Sapphire", artist="Ed Sheeran",
            duration_seconds=180, provider="dz",
        )
    app_obj = client._transport.app  # ASGITransport exposes the app
    app_obj.state.provider.get_info = fake_info.__get__(app_obj.state.provider)
    r = await client.get(
        "/similar/dz:555", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 200
    assert seen["deezer_id"] == "555"


@pytest.mark.asyncio
async def test_suggest_enriched_with_live_titles(client, monkeypatch):
    async def fake_suggest(self, q, limit=10):
        return ["Kesariya", "Tum Hi Ho"]
    monkeypatch.setattr(DiscoveryClient, "suggest", fake_suggest)
    r = await client.get("/api/suggest", params={"q": "kesa"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "Kesariya" in body["suggestions"]
