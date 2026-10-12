"""Tests for discovery: lyrics (lrclib), similar (Deezer), suggest."""
import json
import pytest
import httpx

from app.services.discovery import (
    DiscoveryClient,
    DiscoveryNotFoundError,
    DiscoveryUnavailableError,
    LyricsNotFoundError,
)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _resp(status: int, body) -> httpx.Response:
    return httpx.Response(
        status,
        headers={"content-type": "application/json"},
        content=json.dumps(body).encode(),
    )


LRC = {"trackName": "Hello", "artistName": "Adele", "albumName": "25",
       "duration": 295, "syncedLyrics": "[00:01.00] hi", "plainLyrics": "hi"}


class TestLyrics:
    def _disc(self, handler):
        return DiscoveryClient(http=_client(handler))

    def test_exact_lookup(self):
        def h(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/get"
            assert request.url.params["track_name"] == "Hello"
            return _resp(200, LRC)
        d = self._disc(h)
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(
            d.lyrics("Hello", "Adele", "25", 295)
        )
        assert out["synced"] == "[00:01.00] hi"
        assert out["source"] == "lrclib"

    def test_fallback_search_duration_window(self):
        def h(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/get":
                return _resp(404, {"message": "not found"})
            assert request.url.path == "/api/search"
            return _resp(200, [
                {**LRC, "duration": 500},          # too far -> skipped
                {**LRC, "duration": 300},          # within slack -> picked
            ])
        d = self._disc(h)
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(d.lyrics("Hello", None, None, 295))
        assert out["synced"] == "[00:01.00] hi"

    def test_no_match_raises(self):
        d = self._disc(lambda r: _resp(404, {}))
        import asyncio
        with pytest.raises(LyricsNotFoundError):
            asyncio.get_event_loop().run_until_complete(d.lyrics("Nope"))

    def test_cache_second_call_no_upstream(self):
        calls = []
        def h(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return _resp(200, LRC)
        d = self._disc(h)
        import asyncio
        async def both():
            a = await d.lyrics("Hello", "Adele", None, 295)
            b = await d.lyrics("Hello", "Adele", None, 295)
            return a, b
        asyncio.get_event_loop().run_until_complete(both())
        assert len(calls) == 1


class TestSimilar:
    SEED = {"trackId": 1, "trackName": "Shape of You", "artistName": "Ed Sheeran",
            "collectionId": 500, "trackTimeMillis": 234000,
            "artworkUrl100": "https://a/100x100bb.jpg"}
    TR2 = {"trackId": 2, "trackName": "Castle on the Hill", "artistName": "Ed Sheeran",
           "trackTimeMillis": 261000, "artworkUrl100": "https://a/2.jpg"}
    TR3 = {"trackId": 3, "trackName": "Perfect", "artistName": "Ed Sheeran"}

    def _iT(self, request: httpx.Request, extra_tracks=None):
        # routed by host+path so iTunes and Deezer mocks can share one handler
        if request.url.host == "itunes.apple.com":
            if request.url.path == "/search":
                if request.url.params.get("attribute") == "artistTerm":
                    return _resp(200, {"results": extra_tracks or []})
                return _resp(200, {"results": [self.SEED]})
            return _resp(200, {"results": [
                {"kind": "song", **self.TR2}, {"kind": "song", **self.TR3},
            ]})
        return _resp(404, {})

    def test_itunes_album_then_artist(self):
        def handler(request):
            return self._iT(request, extra_tracks=[
                {"trackId": 9, "trackName": "Thinking Out Loud",
                 "artistName": "Ed Sheeran"}
            ])
        d = DiscoveryClient(http=_client(handler))
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(
            d.similar("Shape of You", "Ed Sheeran", limit=3)
        )
        assert [x["media_id"] for x in out] == ["am:2", "am:3", "am:9"]
        assert out[0]["provider"] == "am"
        assert out[0]["duration_seconds"] == 261
        assert out[0]["thumbnail_url"] == "https://a/2.jpg"

    def test_artwork_resize_rewrite(self):
        item = dict(self.SEED)
        out = DiscoveryClient._map_itunes_batch([item], 1)
        assert out[0]["thumbnail_url"] == "https://a/300x300bb.jpg"

    def test_deezer_fallback_for_native_id(self):
        def handler(request):
            if request.url.host == "itunes.apple.com":
                return _resp(200, {"results": []})
            assert request.url.path == "/track/555/similar"
            return _resp(200, {"data": [
                {"id": 7, "title": "Z", "artist": {"name": "Q"}, "album": {}}
            ]})
        d = DiscoveryClient(http=_client(handler))
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(
            d.similar("t", "a", deezer_id="555")
        )
        assert out[0]["media_id"] == "dz:7"

    def test_no_source_raises_not_found(self):
        def handler(request):
            if request.url.host == "itunes.apple.com":
                return _resp(200, {"results": []})
            return _resp(200, {"data": []})
        d = DiscoveryClient(http=_client(handler))
        import asyncio
        with pytest.raises(DiscoveryNotFoundError):
            asyncio.get_event_loop().run_until_complete(d.similar("x", "y"))

    def test_upstream_error_dict_surfaces_unavailable(self):
        def handler(request):
            return _resp(200, {"error": {"message": "rate limit"}})
        d = DiscoveryClient(http=_client(handler))
        import asyncio
        with pytest.raises(DiscoveryUnavailableError):
            asyncio.get_event_loop().run_until_complete(d.similar("x", "y"))


class TestSuggest:
    def test_titles_deduped_capped(self):
        def h(request: httpx.Request) -> httpx.Response:
            assert request.url.params["q"] == "arijit"
            return _resp(200, {"data": [
                {"title": "Kesariya"}, {"title": "kesariya "},
                {"title": "Tum Hi Ho"}, {"title": ""},
                {"title": "Channa"}, {"title": "Raabta"},
            ]})
        d = DiscoveryClient(http=_client(h))
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(d.suggest("arijit", limit=2))
        assert out == ["Kesariya", "Tum Hi Ho"]

    def test_upstream_down_returns_empty(self):
        def h(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down", request=request)
        d = DiscoveryClient(http=_client(h))
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(d.suggest("q"))
        assert out == []
