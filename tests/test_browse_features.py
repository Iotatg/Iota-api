"""Catalogue browse + transcript feature tests.

Covers: Deezer discovery methods (charts/radios/genres/artists/albums/
entity/playlist), id normalisation helpers, VTT parsing, provider
get_transcript behaviour, and the browse route error mapping.
"""
from __future__ import annotations

import pytest

from app.services.discovery import (
    DiscoveryClient,
    DiscoveryNotFoundError,
    DiscoveryUnavailableError,
    looks_like_deezer_playlist,
)
from app.services.youtube_provider import (
    YouTubeProvider,
    _YtdlpResult,
    _vtt_seconds,
    parse_vtt,
)
from app.services.media_provider import (
    MediaNotFoundError,
    ProviderUnavailableError,
)


# ── id helpers ─────────────────────────────────────────────────────────
def test_strip_and_playlist_ids():
    assert DiscoveryClient.strip_id("dzradio:42") == "42"
    assert DiscoveryClient.strip_id("  dzalbum:7 ") == "7"
    assert DiscoveryClient.strip_id("https://www.deezer.com/track/99") == "99"
    assert DiscoveryClient.playlist_id("dz:6862354041") == "6862354041"
    assert DiscoveryClient.playlist_id(
        "https://www.deezer.com/playlist/123?foo=1") == "123"
    assert looks_like_deezer_playlist("dz:9")
    assert looks_like_deezer_playlist("https://www.deezer.com/playlist/9")
    assert not looks_like_deezer_playlist("PLabc123")


# ── Deezer client methods ──────────────────────────────────────────────
def _client_with(handler):
    disc = DiscoveryClient()

    async def fake_get_json(url, params=None, headers=None):
        return handler(url, params or {})
    disc._get_json = fake_get_json  # type: ignore[assignment]
    return disc


@pytest.mark.asyncio
async def test_charts_rows_and_kind_guard():
    disc = _client_with(
        lambda url, p: {"data": [{"id": 5, "title": "T", "duration": 200,
                                  "artist": {"name": "A"},
                                  "album": {"title": "AL", "cover_xl": "c"}}]}
    )
    rows = await disc.charts("tracks", limit=10)
    assert rows[0]["id"] == "dztrack:5" and rows[0]["artist"] == "A"
    with pytest.raises(DiscoveryNotFoundError):
        await disc.charts("singles", limit=5)
    disc2 = _client_with(lambda url, p: {"error": {"message": "boom"}})
    with pytest.raises(DiscoveryUnavailableError):
        await disc2.charts("albums", limit=5)


@pytest.mark.asyncio
async def test_dz_pages_walks_pagination_and_stops():
    seen_indexes = []

    def handler(url, p):
        seen_indexes.append(p.get("index"))
        start = p.get("index", 0)
        rows = [{"id": i} for i in range(start, start + p["limit"])]
        return {"data": rows}
    disc = _client_with(handler)
    out = await disc._dz_pages("/x", limit=60)
    assert [r["id"] for r in out] == list(range(60))
    assert seen_indexes == [0, 25, 50]

    disc_short = _client_with(
        lambda url, p: {"data": [{"id": 1}, {"id": 2}]})
    assert len(await disc_short._dz_pages("/x", limit=50)) == 2


@pytest.mark.asyncio
async def test_radios_and_radio_tracks():
    def handler(url, p):
        if "/radio/5/tracks" in url:
            return {"data": [{"id": 9, "title": "s", "duration": 3,
                              "artist": {"name": "x"}, "album": {}}]}
        if url.endswith("/radio"):
            return {"data": [{"id": 5, "title": "Relax", "description": "d"}]}
        return None
    disc = _client_with(handler)
    rows = await disc.radios(limit=10)
    assert rows[0]["id"] == "dzradio:5" and rows[0]["title"] == "Relax"
    tracks = await disc.radio_tracks("dzradio:5", limit=5)
    assert tracks[0]["id"] == "dztrack:9"

    disc_none = _client_with(lambda url, p: None)
    with pytest.raises(DiscoveryUnavailableError):
        await disc_none.radios(limit=5)
    with pytest.raises(DiscoveryNotFoundError):
        await disc_none.radio_tracks("999", limit=5)


@pytest.mark.asyncio
async def test_genres_and_catalog_search():
    disc = _client_with(
        lambda url, p: {"data": [{"id": 132, "name": "Pop"}]} if url.endswith("/genre")
        else {"data": [{"id": 1, "name": "Pop", "picture_xl": "p"}]}
    )
    genres = await disc.genres()
    assert genres == [{"id": 132, "name": "Pop", "picture": None}]
    artists = await disc.catalog_search("artists", "pop", limit=5)
    assert artists[0]["id"] == "dzartist:1"
    with pytest.raises(DiscoveryNotFoundError):
        await disc.catalog_search("tracks", "x", limit=5)


@pytest.mark.asyncio
async def test_artist_by_name_and_album():
    def handler(url, p):
        if "/search/artist" in url:
            return {"data": [{"id": 1300, "name": "Adele"}]}
        if "/artist/1300/top" in url:
            return {"data": [{"id": 66, "title": "Hello", "duration": 300,
                              "artist": {"name": "Adele"}, "album": {}}]}
        if "/artist/1300/related" in url:
            return {"data": [{"id": 7, "name": "Similar"}]}
        if "/artist/1300/albums" in url:
            return {"data": [{"id": 900, "title": "21", "release_date": "2011",
                              "tracks": {"nb": 11}, "artist": {"name": "Adele"}}]}
        if url.endswith("/artist/1300"):
            return {"id": 1300, "name": "Adele", "nb_fan": 1, "nb_album": 2,
                    "radio": True}
        return None
    disc = _client_with(handler)
    blob = await disc.artist("adele", limit=10)
    assert blob["id"] == "dzartist:1300"
    assert blob["albums"][0]["id"] == "dzalbum:900"
    assert blob["top_tracks"][0]["id"] == "dztrack:66"
    assert blob["similar_artists"][0]["name"] == "Similar"

    with pytest.raises(DiscoveryNotFoundError):
        await _client_with(lambda url, p: None).artist("zzz", limit=5)


@pytest.mark.asyncio
async def test_album_and_playlist_tracks():
    def handler(url, p):
        if "/album/9/tracks" in url:
            return {"data": [{"id": 1, "title": "t", "duration": 2,
                              "artist": {"name": "a"}, "album": {}}]}
        if url.endswith("/album/9"):
            return {"id": 9, "title": "AL", "artist": {"name": "a"},
                    "nb_tracks": 1}
        if "/playlist/99/tracks" in url:
            return {"data": [{"id": 3, "title": "p", "artist": {"name": "x"},
                              "album": {}}]}
        if url.endswith("/playlist/99"):
            return {"id": 99, "title": "Mood", "user": {"name": "u"},
                    "nb_tracks": 1}
        return None
    disc = _client_with(handler)
    album = await disc.album("dzalbum:9", limit=5)
    assert album["tracks"][0]["id"] == "dztrack:1"
    pl = await disc.playlist_tracks("dz:99", limit=5)
    assert pl["title"] == "Mood" and pl["creator"] == "u"
    with pytest.raises(DiscoveryNotFoundError):
        await disc.album("nothing-matches", limit=5)


@pytest.mark.asyncio
async def test_unknown_deezer_object_maps_to_not_found():
    def no_data(url, p):
        raise DiscoveryUnavailableError(f"{url} error: no data")
    disc = _client_with(no_data)
    with pytest.raises(DiscoveryNotFoundError):
        await disc.album("999999999", limit=5)
    with pytest.raises(DiscoveryNotFoundError):
        await disc.playlist_tracks("dz:0", limit=5)

    def hard_down(url, p):
        raise DiscoveryUnavailableError(f"{url} timed out")
    with pytest.raises(DiscoveryUnavailableError):
        await _client_with(hard_down).album("9", limit=5)


# ── VTT parsing ────────────────────────────────────────────────────────
def test_vtt_seconds_and_parse():
    assert _vtt_seconds("00:01:02.500") == 62.5
    assert _vtt_seconds("01:02,5") == 62.5
    assert _vtt_seconds("junk") == 0.0

    vtt = """WEBVTT
Kind: captions
Language: en

00:00:01.860 --> 00:00:04.120 align:start position:0%
hello world

00:00:01.920 --> 00:00:04.120 align:start position:0%
hello world

00:00:04.130 --> 00:00:06.500
<c>next <b>line</b></c>

00:00:20.000 --> 00:00:22.000
[Music]
done
"""
    segs = parse_vtt(vtt)
    assert [s["text"] for s in segs] == ["hello world", "next line", "done"]
    assert segs[0]["start_seconds"] == 1.86 and segs[1]["start_seconds"] == 4.13


# ── provider transcript ────────────────────────────────────────────────
def _write_vtt(args):
    # yt-dlp appends the language code for subtitle output templates
    out = args[args.index("-o") + 1]
    with open(out.replace("%(ext)s", "en.vtt"), "w") as fh:
        fh.write("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nla la\n")


@pytest.mark.asyncio
async def test_get_transcript_happy_path(monkeypatch):
    calls = []

    async def fake_run(*args, timeout=None):
        calls.append(list(args))
        _write_vtt(list(args))
        return _YtdlpResult(ok=True)
    monkeypatch.setattr("app.services.youtube_provider._run_ytdlp", fake_run)
    prov = YouTubeProvider()
    payload = await prov.get_transcript("yt:dQw4w9WgXcQ", language="en")
    assert payload["media_id"] == "yt:dQw4w9WgXcQ"
    assert payload["segments"] == [{"start_seconds": 1.0, "text": "la la"}]
    assert payload["plain_text"] == "la la" and payload["source"] == "youtube-captions"
    assert "--write-auto-subs" in calls[0] and "dQw4w9WgXcQ" in "".join(calls[0])
    # second call served from cache
    await prov.get_transcript("dQw4w9WgXcQ")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_get_transcript_errors(monkeypatch):
    async def fail(*args, timeout=None):
        return _YtdlpResult(ok=False, stderr="ERROR: Video unavailable")
    monkeypatch.setattr("app.services.youtube_provider._run_ytdlp", fail)
    prov = YouTubeProvider()
    with pytest.raises(MediaNotFoundError):
        await prov.get_transcript("dQw4w9WgXcQ")

    async def fail2(*args, timeout=None):
        return _YtdlpResult(ok=False, stderr="HTTP Error 403")
    monkeypatch.setattr("app.services.youtube_provider._run_ytdlp", fail2)
    with pytest.raises(ProviderUnavailableError):
        await prov.get_transcript("dQw4w9WgXcQ")

    async def ok_nosubs(*args, timeout=None):
        return _YtdlpResult(ok=True)
    monkeypatch.setattr("app.services.youtube_provider._run_ytdlp", ok_nosubs)
    with pytest.raises(MediaNotFoundError):
        await prov.get_transcript("dQw4w9WgXcQ")

    with pytest.raises(MediaNotFoundError):
        await prov.get_transcript("bad!!")
    # unsafe lang is sanitised, never injected into argv
    captured = []

    async def capture(*args, timeout=None):
        captured.append(list(args))
        return _YtdlpResult(ok=True)
    monkeypatch.setattr("app.services.youtube_provider._run_ytdlp", capture)
    with pytest.raises(MediaNotFoundError):
        await prov.get_transcript("dQw4w9WgXcQ", language="en;rm -rf")
    assert "en,en-orig,en-*" in captured[0]


# ── routes ─────────────────────────────────────────────────────────────
class _StubDisc:
    def __init__(self):
        self.calls = []

    async def charts(self, kind, limit):
        self.calls.append(("charts", kind, limit))
        if kind == "singles":
            raise DiscoveryNotFoundError("unknown chart")
        if kind == "albums":
            raise DiscoveryUnavailableError("dz down")
        return [{"id": "dztrack:1", "title": "T"}]

    async def playlist_tracks(self, value, limit):
        self.calls.append(("pl", value, limit))
        raise DiscoveryNotFoundError("no playlist")


@pytest.mark.asyncio
async def test_charts_route_ok_and_errors(client, created_key, app_instance):
    stub = _StubDisc()
    app_instance.state.discovery_client = stub
    key = created_key["api_key"]

    r = await client.get("/charts", params={"kind": "tracks", "key": key})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] and body["results"][0]["id"] == "dztrack:1"

    r = await client.get("/charts", params={"kind": "singles", "key": key})
    assert r.status_code == 404
    assert r.json()["error"] == "chart_not_found"

    r = await client.get("/charts", params={"kind": "albums", "key": key})
    assert r.status_code == 502
    assert r.json()["error"] == "chart_upstream_error"

    r = await client.get("/charts", params={"kind": "tracks"})
    assert r.status_code in (401, 403)


class _StubDisc2(_StubDisc):
    async def playlist_tracks(self, value, limit):
        self.calls.append(("pl", value, limit))
        return {"id": "dzplaylist:9", "title": "Mood", "tracks": []}

    async def radios(self, limit):
        raise DiscoveryUnavailableError("dz down")

    async def genres(self):
        return [{"id": 1, "name": "Pop", "picture": None}]


@pytest.mark.asyncio
async def test_deezer_playlist_branch_and_map_errors(client, created_key, app_instance):
    stub = _StubDisc2()
    app_instance.state.discovery_client = stub
    key = created_key["api_key"]

    r = await client.get("/playlists/dz:9", params={"key": key})
    assert r.status_code == 200 and r.json()["source"] == "deezer"
    assert stub.calls[0][0] == "pl"

    r = await client.get("/radios", params={"key": key})
    assert r.status_code == 502

    r = await client.get("/genres", params={"key": key})
    assert r.status_code == 200 and r.json()["count"] == 1
