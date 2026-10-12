"""Tests for the native upstream features.

Covers: the player-client rotation failover (rotation_stream + relay
routing), discovery.suggest parsing, the lyrics.ovh fallback chain,
views propagation through provider/registry/schema, the yt circuit
breaker, and the /suggest /trending /playlists routes.
"""
from __future__ import annotations

import json

import pytest

from app.dependencies import get_provider
from app.services.discovery import (
    DiscoveryClient,
    DiscoveryNotFoundError,
    DiscoveryUnavailableError,
)
from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    ProviderUnavailableError,
)
from app.services.provider_registry import ProviderRegistry, find_youtube_provider
from app.services.stream_fallback import _youtube_video_id, relay_source
from app.services.youtube_provider import (
    YouTubeProvider,
    _YtdlpResult,
    _run_ytdlp,
    breaker_is_open,
    breaker_reset,
)


# ── relay id guard ────────────────────────────────────────────────────
def test_youtube_video_id_guard():
    assert _youtube_video_id("yt:dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _youtube_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _youtube_video_id("sp:1234") == ""
    assert _youtube_video_id("yt:not-an-id") == ""
    assert _youtube_video_id("") == ""


def test_find_youtube_provider():
    yt = YouTubeProvider()
    reg = ProviderRegistry([yt])
    assert find_youtube_provider(reg) is yt
    assert find_youtube_provider(yt) is yt
    assert find_youtube_provider(ProviderRegistry([YouTubeProvider()])) is not None

    class Other:
        name = "dz"
        enabled = True
        async def get_info(self, mid): ...
        async def get_stream(self, mid): ...
        async def search(self, q, limit=20): return []

    assert find_youtube_provider(ProviderRegistry([Other()])) is None


# ── rotation_stream (native failover) ─────────────────────────────────
@pytest.mark.asyncio
async def test_rotation_hit_warms_caches(monkeypatch):
    prov = YouTubeProvider()
    calls = []

    async def fake_once(argv, timeout):
        calls.append(argv)
        payload = {"id": "dQw4w9WgXcQ", "title": "Song",
                   "channel": "Chan", "duration": 200,
                   "view_count": 10, "url": "https://cdn/x?a=1"}
        if "player_client=tv" in " ".join(argv):
            return _YtdlpResult(ok=True, data=(
                json.dumps(payload).encode() + b"\n"))
        return _YtdlpResult(ok=False, stderr="Sign in to confirm")

    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", fake_once)
    src = await prov.rotation_stream("yt:dQw4w9WgXcQ", kind="audio")
    assert src is not None
    assert src.direct_url == "https://cdn/x?a=1"
    assert src.mime_type == "audio/mpeg"
    # tv is the first rotation client; no further attempts were made
    assert len(calls) == 1
    assert "player_client=tv" in " ".join(calls[0])
    assert "bestaudio/best" in " ".join(calls[0])
    # cookies are stripped from rotation calls (flagged sessions poison
    # these clients too)
    assert "--cookies" not in " ".join(calls[0])


@pytest.mark.asyncio
async def test_rotation_video_selector_and_all_fail(monkeypatch):
    prov = YouTubeProvider()
    seen = []

    async def always_bad(argv, timeout):
        seen.append(" ".join(argv))
        return _YtdlpResult(ok=False, stderr="Sign in to confirm")

    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", always_bad)
    assert await prov.rotation_stream("dQw4w9WgXcQ", kind="video") is None
    assert len(seen) == len(YouTubeProvider._FALLBACK_CLIENTS)
    assert "player_client=tv_simply" in seen[-1]
    assert "18/best[height<=?360]" in seen[0]

    # non-video ids are rejected before any subprocess
    assert await prov.rotation_stream("sp:1234", kind="audio") is None


@pytest.mark.asyncio
async def test_rotation_skips_bad_json_and_urlless(monkeypatch):
    prov = YouTubeProvider()
    n = {"i": 0}

    async def flaky(argv, timeout):
        n["i"] += 1
        if n["i"] == 1:
            return _YtdlpResult(ok=True, data=b"not json")
        if n["i"] == 2:
            return _YtdlpResult(ok=True,
                                data=b'{"id": "x", "url": "ftp://no"}\n')
        return _YtdlpResult(ok=True,
                            data=b'{"id": "x", "url": "https://ok/u"}\n')

    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", flaky)
    src = await prov.rotation_stream("dQw4w9WgXcQ")
    assert src is not None and src.direct_url == "https://ok/u"
    assert n["i"] == 3


# ── relay_source routing ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_relay_uses_rotation_on_registry(monkeypatch):
    from app.services.media_provider import StreamSource

    class Yt:
        name = "yt"
        enabled = True
        captured = {}

        async def get_info(self, mid): ...
        async def get_stream(self, mid): ...
        async def search(self, q, limit=20): return []

        async def rotation_stream(self, vid, kind="audio"):
            Yt.captured = (vid, kind)
            return StreamSource(storage_key="", size_bytes=0,
                                mime_type="video/mp4", direct_url="u")

    yt = Yt()
    reg = ProviderRegistry([yt])
    src = await relay_source(reg, "yt:dQw4w9WgXcQ", "video")
    assert src is not None and src.direct_url == "u"
    assert Yt.captured == ("dQw4w9WgXcQ", "video")

    assert await relay_source(reg, "dz:12345", "video") is None
    assert Yt.captured == ("dQw4w9WgXcQ", "video")  # untouched


# ── suggest ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_suggest_google_parse_and_walled():
    disc = DiscoveryClient.__new__(DiscoveryClient)
    disc._cache = {}

    async def google_ok(url, params=None, headers=None):
        assert "suggestqueries" in url
        return ["shape", ["shape of you", " shape of you lyrics", ""]]
    disc._get_json = google_ok  # type: ignore[assignment]
    out = await disc.youtube_suggest("shape", limit=5)
    assert out == ["shape of you", "shape of you lyrics"]

    async def google_down(url, params=None, headers=None):
        raise DiscoveryUnavailableError("walled")
    disc._get_json = google_down  # type: ignore[assignment]
    disc._cache.clear()
    assert await disc.youtube_suggest("nub", limit=5) == []


# ── lyrics fallback chain ─────────────────────────────────────────────
def _disc():
    disc = DiscoveryClient.__new__(DiscoveryClient)
    disc._cache = {}
    return disc


@pytest.mark.asyncio
async def test_lyrics_ovh_after_lrclib_miss():
    disc = _disc()

    async def fake(url, params=None, headers=None):
        if url.startswith("https://lrclib"):
            return None
        assert url.startswith("https://api.lyrics.ovh/v1/")
        assert "Ed%20Sheeran" in url and "Shape" in url
        return {"lyrics": " We are back to January "}
    disc._get_json = fake
    out = await disc.lyrics("Shape of You", "Ed Sheeran")
    assert out["source"] == "lyrics.ovh"
    assert out["plain"] == "We are back to January"
    assert out["synced"] is None


@pytest.mark.asyncio
async def test_lyrics_lrclib_down_still_502_without_ovh():
    disc = _disc()

    async def fake(url, params=None, headers=None):
        if url.startswith("https://api.lyrics.ovh"):
            return None
        raise DiscoveryUnavailableError("lrclib 503")
    disc._get_json = fake
    with pytest.raises(DiscoveryUnavailableError):
        await disc.lyrics("Song", "Artist")


@pytest.mark.asyncio
async def test_lyrics_lrclib_ok_skips_ovh():
    disc = _disc()

    async def fake(url, params=None, headers=None):
        assert url.startswith("https://lrclib")
        return {"trackName": "S", "artistName": "A",
                "syncedLyrics": "[00:01] hi", "plainLyrics": None}
    disc._get_json = fake
    out = await disc.lyrics("S", "A")
    assert out["source"] == "lrclib" and out["synced"] == "[00:01] hi"


@pytest.mark.asyncio
async def test_lyrics_ovh_soft_failure_preserves_lrclib_outcome():
    disc = _disc()

    async def fake(url, params=None, headers=None):
        if url.startswith("https://api.lyrics.ovh"):
            raise DiscoveryUnavailableError("ovh down")
        return None
    disc._get_json = fake
    with pytest.raises(DiscoveryNotFoundError):
        await disc.lyrics("Song", "Artist")


# ── views propagation ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_registry_preserves_views():
    class P:
        name = "vv"
        enabled = True
        async def get_info(self, mid):
            return MediaMetadata(media_id=mid, title="t", views=42, likes=7,
                                 provider=self.name)
        async def get_stream(self, mid): ...
        async def search(self, q, limit=20):
            return [MediaMetadata(media_id="a", title="a", views=42,
                                  provider=self.name)]

    reg = ProviderRegistry([P()])
    meta = await reg.get_info("vv:x")
    assert meta.views == 42 and meta.likes == 7
    rows = await reg.search("q")
    assert rows[0].views == 42


# ── provider failure keeps original 503 semantics ────────────────────
class _UnavailableProvider:
    name = "yt"

    async def get_info(self, mid):
        raise ProviderUnavailableError("bot check")

    async def get_stream(self, mid):
        raise ProviderUnavailableError("bot check")

    async def get_stream_by_type(self, mid, kind="audio", **kw):
        raise ProviderUnavailableError("bot check")

    async def search(self, q, limit=20):
        return []


@pytest.mark.asyncio
async def test_info_route_503_when_provider_down(client, created_key, app_instance):
    app_instance.dependency_overrides[get_provider] = lambda: _UnavailableProvider()
    r = await client.get(
        "/info/yt:dQw4w9WgXcQ", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_search_route_empty_passes_through(client, created_key, app_instance):
    app_instance.dependency_overrides[get_provider] = lambda: _UnavailableProvider()
    r = await client.get(
        "/search", params={"q": "shape", "key": created_key["api_key"]}
    )
    assert r.status_code == 200
    assert r.json()["count"] == 0


# ── circuit breaker ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_circuit_opens_after_marker_failures(monkeypatch):
    breaker_reset()
    monkeypatch.setattr(
        "app.services.youtube_provider._resolve_ytdlp_argv", lambda: ["yt-dlp"]
    )

    async def failing_once(argv, timeout):
        return _YtdlpResult(ok=False, stderr="Sign in to confirm you're not a bot")
    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", failing_once)

    for _ in range(3):
        res = await _run_ytdlp("dummy target")
        assert not res.ok
    assert breaker_is_open()
    # fast-fail while open — no subprocess attempts
    called = 0

    async def no_call(argv, timeout):
        nonlocal called
        called += 1
        return _YtdlpResult(ok=True)
    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", no_call)
    res = await _run_ytdlp("dummy target")
    assert not res.ok and "circuit breaker" in res.stderr and called == 0
    breaker_reset()
    assert not breaker_is_open()


@pytest.mark.asyncio
async def test_success_resets_breaker_streak(monkeypatch):
    breaker_reset()
    monkeypatch.setattr(
        "app.services.youtube_provider._resolve_ytdlp_argv", lambda: ["yt-dlp"]
    )
    seq = [
        _YtdlpResult(ok=False, stderr="HTTP Error 429: Too Many Requests"),
        _YtdlpResult(ok=True, data=b"{}"),
        _YtdlpResult(ok=False, stderr="HTTP Error 429: Too Many Requests"),
    ]
    it = iter(seq)

    async def next_once(argv, timeout):
        return next(it)
    monkeypatch.setattr("app.services.youtube_provider._ytdlp_once", next_once)
    for _ in range(3):
        await _run_ytdlp("dummy")
    assert not breaker_is_open()  # streak never reached 3 in a row
    breaker_reset()


# ── trending / playlist parsing ───────────────────────────────────────
@pytest.mark.asyncio
async def test_trending_and_playlist_rows(monkeypatch):
    prov = YouTubeProvider()
    payload = {"title": "Mix", "entries": [
        {"id": "dQw4w9WgXcQ", "title": "A", "channel": "C",
         "duration": 200, "view_count": 5, "thumbnail": "t"},
        {"id": "bad"},
        {"id": "JGwWNGJdvx8", "title": "B", "view_count": "not-int"},
        {"id": "dQw4w9WgXcQ", "title": "dup"},
    ]}

    async def fake_flat(self, target, playlist_end=0):
        assert "playlist" in target or "trending" in target
        return payload
    monkeypatch.setattr(YouTubeProvider, "_ytdlp_flat_json", fake_flat)

    rows = await prov.trending(limit=10)
    assert [r.media_id for r in rows] == ["dQw4w9WgXcQ", "JGwWNGJdvx8"]
    assert rows[0].views == 5 and rows[1].views is None

    title, entries = await prov.get_playlist("PLabc123def456", limit=10)
    assert title == "Mix" and len(entries) == 2

    with pytest.raises(MediaNotFoundError):
        await prov.get_playlist("not-a-playlist", limit=5)
