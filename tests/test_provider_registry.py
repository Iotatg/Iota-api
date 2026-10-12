"""Tests for the ProviderRegistry.

These tests use a FakeProvider instead of the real YouTube/Spotify/etc.
implementations so they exercise only the registry's dispatch + fan-out
logic. The real providers are tested in their own modules.
"""
from __future__ import annotations

import pytest

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)
from app.services.provider_registry import (
    DEMO_BARE_ALIAS,
    ProviderRegistry,
)


class FakeProvider(MediaProvider):
    """Minimal provider for registry tests. Configurable per-method."""

    def __init__(
        self,
        name: str,
        *,
        enabled: bool = True,
        search_results=None,
        info: MediaMetadata = None,
        stream: StreamSource = None,
        raise_on_search: Exception = None,
    ) -> None:
        self.name = name
        self._enabled = enabled
        self._search_results = search_results or []
        self._info = info
        self._stream = stream
        self._raise_on_search = raise_on_search

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def search(self, query, limit=20):
        if self._raise_on_search is not None:
            raise self._raise_on_search
        return self._search_results[:limit]

    async def get_info(self, media_id):
        if self._info is None:
            raise MediaNotFoundError(media_id)
        return self._info

    async def get_stream(self, media_id):
        if self._stream is None:
            raise MediaNotFoundError(media_id)
        return self._stream


def _meta(provider: str, media_id: str, title: str = "T") -> MediaMetadata:
    return MediaMetadata(
        media_id=media_id, title=title, provider=provider,
        storage_key="", mime_type="audio/mpeg",
    )


def _stream(provider: str, media_id: str, direct_url: str = None) -> StreamSource:
    return StreamSource(
        storage_key=media_id, size_bytes=0, mime_type="audio/mpeg",
        direct_url=direct_url,
    )


class TestSplit:
    def test_bare_id_routes_to_demo(self):
        reg = ProviderRegistry([FakeProvider("demo")])
        assert reg.split("sample-001.mp3") == (DEMO_BARE_ALIAS, "sample-001.mp3")

    def test_prefixed_id(self):
        reg = ProviderRegistry([FakeProvider("yt")])
        assert reg.split("yt:dQw4w9WgXcQ") == ("yt", "dQw4w9WgXcQ")

    def test_empty_raises(self):
        reg = ProviderRegistry([FakeProvider("demo")])
        with pytest.raises(MediaNotFoundError):
            reg.split("")

    def test_colon_only_raises(self):
        reg = ProviderRegistry([FakeProvider("demo")])
        with pytest.raises(MediaNotFoundError):
            reg.split(":abc")
        with pytest.raises(MediaNotFoundError):
            reg.split("yt:")


class TestRegistryConstruction:
    def test_disabled_provider_dropped(self):
        reg = ProviderRegistry([
            FakeProvider("demo", enabled=True),
            FakeProvider("yt", enabled=False),
        ])
        assert "yt" not in reg.providers
        assert "demo" in reg.providers

    def test_no_enabled_raises(self):
        with pytest.raises(RuntimeError):
            ProviderRegistry([FakeProvider("demo", enabled=False)])


class TestDispatch:
    def test_get_info_uses_prefix(self):
        info = _meta("yt", "abc", title="Hello")
        yt = FakeProvider("yt", info=info)
        reg = ProviderRegistry([FakeProvider("demo"), yt])
        result = reg.get_info_sync if hasattr(reg, "get_info_sync") else None
        import asyncio
        meta = asyncio.get_event_loop().run_until_complete(reg.get_info("yt:abc"))
        assert meta.title == "Hello"
        assert meta.media_id == "yt:abc"

    def test_unknown_prefix_raises(self):
        reg = ProviderRegistry([FakeProvider("demo")])
        import asyncio
        with pytest.raises(MediaNotFoundError):
            asyncio.get_event_loop().run_until_complete(reg.get_info("zz:abc"))

    def test_get_stream_delegates(self):
        src = _stream("yt", "abc", direct_url="https://x.test/stream")
        yt = FakeProvider("yt", stream=src)
        reg = ProviderRegistry([yt])
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(reg.get_stream("yt:abc"))
        assert out.direct_url == "https://x.test/stream"

    def test_get_stream_by_type_delegates(self):
        src = _stream("yt", "abc", direct_url="https://x.test/video.mp4")
        yt = FakeProvider("yt", stream=src)
        reg = ProviderRegistry([yt])
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(
            reg.get_stream_by_type("yt:abc", "video")
        )
        # FakeProvider inherits the ABC default, which ignores the
        # media type and defers to get_stream.
        assert out.direct_url == "https://x.test/video.mp4"


class TestSearchFanOut:
    def test_fan_out_merges_and_prefixes(self):
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            yt = FakeProvider("yt", search_results=[_meta("yt", "v1", "YT one")])
            sp = FakeProvider("sp", search_results=[_meta("sp", "v2", "SP one")])
            reg = ProviderRegistry([FakeProvider("demo"), yt, sp])
            out = loop.run_until_complete(reg.search("hello", limit=10))
            ids = {m.media_id for m in out}
            assert "yt:v1" in ids
            assert "sp:v2" in ids
        finally:
            loop.close()

    def test_search_dedup_by_canonical_id(self):
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            yt = FakeProvider("yt", search_results=[_meta("yt", "dup", "same")])
            sp = FakeProvider("sp", search_results=[_meta("sp", "dup", "same")])
            reg = ProviderRegistry([yt, sp])
            out = loop.run_until_complete(reg.search("q", limit=10))
            assert len(out) == 1
        finally:
            loop.close()

    def test_search_provider_failure_does_not_abort(self):
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            yt = FakeProvider("yt", search_results=[_meta("yt", "v1", "ok")])
            bad = FakeProvider("sp", raise_on_search=RuntimeError("down"))
            reg = ProviderRegistry([yt, bad])
            out = loop.run_until_complete(reg.search("q", limit=10))
            assert len(out) == 1
            assert out[0].media_id == "yt:v1"
        finally:
            loop.close()

    def test_search_empty_query(self):
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            reg = ProviderRegistry([FakeProvider("demo")])
            assert loop.run_until_complete(reg.search("")) == []
            assert loop.run_until_complete(reg.search("   ")) == []
        finally:
            loop.close()
