"""Tests for the bundled cached-track last-resort fallback."""
from __future__ import annotations

import json
import re

import pytest

from app.services import cached_tracks
from app.services.stream_fallback import relay_source

_INDEX = cached_tracks._INDEX_PATH


def _real_entry():
    items = cached_tracks._load_index()
    vid = next(v for v, e in items.items() if e.get("ext") == "mp3")
    return vid, items[vid]


class _FakeYt:
    name = "yt"

    def __init__(self, result=None):
        self._result = result
        self.calls = 0

    async def rotation_stream(self, vid, kind="audio"):
        self.calls += 1
        return self._result


class _Registry:
    def __init__(self, yt):
        self.providers = {"yt": yt} if yt else {}


class _Ctx:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


class _FakeResp:
    def __init__(self, status, content=b""):
        self.status_code = status
        self.content = content


class _FakeClient:
    def __init__(self, resp=None, error=None, **kwargs):
        self.resp, self.error = resp, error
        self.seen_headers = None

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.seen_headers = headers
        if self.error:
            raise self.error
        return self.resp


def test_bundle_exists_and_valid():
    assert _INDEX.is_file(), "cached_tracks.json must ship with the image"
    items = json.loads(_INDEX.read_text(encoding="utf-8"))
    assert len(items) > 3000
    url_re = re.compile(r"^https://files\.catbox\.moe/[A-Za-z0-9 _-]{4,32}\.(mp3|m4a|mp4)$", re.I)
    id_re = re.compile(r"^[A-Za-z0-9_-]{11}$")
    assert all(id_re.fullmatch(str(i.get("id", ""))) for i in items)
    assert all(url_re.fullmatch(str(i.get("url", ""))) for i in items)
    assert all(str(i.get("title", "")) for i in items)


def test_load_index_dedups_and_rejects_bad_urls(monkeypatch, tmp_path):
    bogus = tmp_path / "idx.json"
    bogus.write_text(json.dumps([
        {"id": "AAAAAAAAAAA", "title": "ok", "url": "https://files.catbox.moe/aaaa.mp3", "mime": "audio/mpeg", "ext": "mp3"},
        {"id": "AAAAAAAAAAA", "title": "dupe", "url": "https://files.catbox.moe/bbbb.mp3", "mime": "audio/mpeg", "ext": "mp3"},
        {"id": "BBBBBBBBBBB", "title": "evil", "url": "https://evil.example.com/x", "mime": "application/x", "ext": "mp3"},
        {"id": "bad!!", "title": "bad id", "url": "https://files.catbox.moe/cccc.mp3", "mime": "audio/mpeg", "ext": "mp3"},
    ]), encoding="utf-8")
    monkeypatch.setattr(cached_tracks, "_entries", None)
    monkeypatch.setattr(cached_tracks, "_INDEX_PATH", bogus)
    table = cached_tracks._load_index()
    assert set(table) == {"AAAAAAAAAAA"}
    assert table["AAAAAAAAAAA"]["title"] == "ok"


def test_lookup_and_enabled(monkeypatch):
    vid, entry = _real_entry()
    assert cached_tracks.lookup(vid) == entry
    assert cached_tracks.lookup("nope") is None
    assert cached_tracks.lookup("") is None
    assert cached_tracks.is_enabled() is True
    monkeypatch.setenv("IOTA_CACHED_FALLBACK", "0")
    assert cached_tracks.is_enabled() is False


def test_sniff_mime():
    assert cached_tracks._sniff_mime(b"ID3\x04\x00\x00\x00\x00\x00\x00", "audio/mp4") == "audio/mpeg"
    assert cached_tracks._sniff_mime(b"\xff\xfb\x90\x64" + b"\x00" * 8, "audio/mp4") == "audio/mpeg"
    assert cached_tracks._sniff_mime(b"\x00\x00\x00\x18ftypdash", "audio/mpeg") == "audio/mp4"
    assert cached_tracks._sniff_mime(b"\x00\x00\x00\x18ftypisom", "video/mp4") == "video/mp4"
    assert cached_tracks._sniff_mime(b"garbagegarbage", "audio/mpeg") == "audio/mpeg"


async def test_refine_mime_uses_generic_headers_and_caches(monkeypatch):
    vid, entry = _real_entry()
    client = _FakeClient(_FakeResp(206, b"\x00\x00\x00\x18ftypdash"))
    monkeypatch.setattr(cached_tracks.httpx, "AsyncClient", client)
    monkeypatch.setattr(cached_tracks, "_sniff_cache", {})
    mime = await cached_tracks.refine_mime(entry)
    assert mime == "audio/mp4"
    assert "python-httpx" not in str(client.seen_headers)
    assert client.seen_headers["User-Agent"].startswith("Mozilla/5.0")
    cached = await cached_tracks.refine_mime(entry)  # served from TTL cache
    assert cached == "audio/mp4"
    assert client.seen_headers["User-Agent"].startswith("Mozilla/5.0")  # unchanged, no refetch


async def test_refine_mime_fail_soft(monkeypatch):
    _, entry = _real_entry()
    monkeypatch.setattr(
        cached_tracks.httpx, "AsyncClient",
        _FakeClient(error=RuntimeError("boom")),
    )
    monkeypatch.setattr(cached_tracks, "_sniff_cache", {})
    assert await cached_tracks.refine_mime(entry) == entry["mime"]


async def test_relay_falls_back_to_catalog_when_rotation_empty(monkeypatch):
    vid, _ = _real_entry()
    yt = _FakeYt(None)
    monkeypatch.setattr(cached_tracks, "_sniff_cache", {
        cached_tracks._load_index()[vid]["url"]: (9e12, "audio/mp4"),
    })
    src = await relay_source(_Registry(yt), f"yt:{vid}")
    assert yt.calls == 1
    assert src is not None
    assert src.direct_url.startswith("https://files.catbox.moe/")
    assert src.mime_type == "audio/mp4"
    assert "catbox" not in src.storage_key
    assert src.size_bytes == 0


async def test_relay_rotation_win_skips_catalog(monkeypatch):
    vid, _ = _real_entry()
    win = object()
    yt = _FakeYt(win)
    src = await relay_source(_Registry(yt), f"yt:{vid}")
    assert src is win


async def test_relay_no_entry_returns_none():
    yt = _FakeYt(None)
    assert await relay_source(_Registry(yt), "yt:zzzzzzzzzzz") is None


async def test_relay_disabled_flag(monkeypatch):
    vid, _ = _real_entry()
    monkeypatch.setenv("IOTA_CACHED_FALLBACK", "off")
    assert await relay_source(_Registry(_FakeYt(None)), f"yt:{vid}") is None


async def test_relay_video_kind_requires_mp4_entry():
    items = cached_tracks._load_index()
    mp3_id = next(v for v, e in items.items() if e["ext"] == "mp3")
    assert await relay_source(_Registry(_FakeYt(None)), f"yt:{mp3_id}", kind="video") is None


async def test_relay_rejects_non_youtube_prefixes():
    yt = _FakeYt(None)
    assert await relay_source(_Registry(yt), "sp:1234") is None
    assert await relay_source(_Registry(yt), "dz:99") is None
