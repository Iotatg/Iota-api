"""Tests for the audio-repair service (/stream?format=m4a|mp3)."""
from __future__ import annotations

import os

import pytest

from app.services import audio_fix
from app.services.audio_fix import (
    FIX_MIME,
    _ffmpeg,
    _ffmpeg_args,
    clamp_mp3_bitrate,
    ensure_fixed_source,
    fixed_key,
)
from app.services.media_provider import StreamSource


class FakeStorage:
    def __init__(self, base: str):
        self.base = base
        self.files: dict[str, int] = {}

    async def exists(self, key):
        return key in self.files

    async def put(self, key, source_path):
        dest = os.path.join(self.base, key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(source_path, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())
        self.files[key] = os.path.getsize(dest)


def _src(url="https://x/y"):
    return StreamSource(storage_key="", size_bytes=0,
                        mime_type="audio/mpeg", direct_url=url)


def _patch_ok(monkeypatch, payload=b"AUDIO"):
    calls = []

    async def fake(fmt, url, out_path, bitrate=None, title=None, artist=None):
        calls.append((fmt, url, bitrate))
        with open(out_path, "wb") as fh:
            fh.write(payload)
        return None
    monkeypatch.setattr(audio_fix, "_ffmpeg", fake)
    return calls


def test_ffmpeg_args_by_format():
    m4a = _ffmpeg_args("m4a", "u", "o.m4a")
    assert "-movflags" in m4a and "+faststart" in m4a and "-c:a" in m4a
    assert "copy" in m4a and "libmp3lame" not in m4a
    mp3 = _ffmpeg_args("mp3", "u", "o.mp3")
    assert "libmp3lame" in mp3 and "faststart" not in " ".join(mp3)
    assert "-b:a" in mp3 and "192k" in mp3
    assert "-q:a" not in mp3
    assert "-i" in m4a and m4a[m4a.index("-i") + 1] == "u"
    tagged = _ffmpeg_args("mp3", "u", "o.mp3", bitrate=256, title="T", artist="A")
    assert "256k" in tagged
    assert "title=T" in tagged and "artist=A" in tagged
    local = _ffmpeg_args("mp3", "/tmp/src.m4a", "o.mp3")
    assert "-user_agent" not in local
    remote = _ffmpeg_args("mp3", "https://cdn.example/a.m4a", "o.mp3")
    assert "-user_agent" in remote


def test_clamp_and_fixed_key_include_bitrate():
    assert clamp_mp3_bitrate(None) == 192
    assert clamp_mp3_bitrate(64) == 64
    assert clamp_mp3_bitrate(320) == 320
    assert clamp_mp3_bitrate(10) == 64
    assert clamp_mp3_bitrate(999) == 320
    assert fixed_key("yt:abc", "mp3") == "fixed/yt_abc-mp3-192.mp3"
    assert fixed_key("yt:abc", "mp3", 256) == "fixed/yt_abc-mp3-256.mp3"
    assert fixed_key("yt:abc", "m4a") == "fixed/yt_abc-m4a.m4a"


@pytest.mark.asyncio
async def test_missing_ffmpeg_reports_not_crashes(tmp_path):
    # A name that cannot exist as an input file: ffmpeg (installed here)
    # fails cleanly rather than raising.
    err = await _ffmpeg("mp3", str(tmp_path / "nope.does-not-exist"),
                        str(tmp_path / "out.mp3"))
    assert err


@pytest.mark.asyncio
async def test_ensure_fixed_creates_then_caches(tmp_path, monkeypatch):
    storage = FakeStorage(str(tmp_path))
    calls = _patch_ok(monkeypatch)
    src = _src()
    out = await ensure_fixed_source(storage, "yt:abc123", src, "mp3")
    assert out is not None and out.mime_type == FIX_MIME["mp3"]
    assert out.storage_key == fixed_key("yt:abc123", "mp3", 192)
    assert await storage.exists(out.storage_key)
    # second call: served from storage, ffmpeg not re-run
    out2 = await ensure_fixed_source(storage, "yt:abc123", src, "mp3")
    assert out2.storage_key == out.storage_key
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_ensure_fixed_fail_soft_and_guards(tmp_path, monkeypatch):
    storage = FakeStorage(str(tmp_path))

    async def boom(fmt, url, out_path, **kwargs):
        return "ffmpeg exploded"
    monkeypatch.setattr(audio_fix, "_ffmpeg", boom)
    assert await ensure_fixed_source(storage, "yt:x", _src(), "m4a") is None

    # no direct url / unknown format -> no repair attempted
    assert await ensure_fixed_source(
        storage, "yt:x", StreamSource("k", 1, "audio/mpeg"), "mp3") is None
    assert await ensure_fixed_source(storage, "yt:x", _src(), "flac") is None


@pytest.mark.asyncio
async def test_fifo_eviction_removes_old_files(tmp_path, monkeypatch):
    storage = FakeStorage(str(tmp_path))
    _patch_ok(monkeypatch)
    monkeypatch.setattr(audio_fix, "_KEEP_FIXED", 2)
    audio_fix._recent.clear()
    for i in range(4):
        src = _src()
        out = await ensure_fixed_source(storage, f"yt:v{i}", src, "m4a")
        assert out is not None
    assert len(audio_fix._recent) == 2
    oldest = fixed_key("yt:v0", "m4a")
    assert not os.path.exists(os.path.join(str(tmp_path), oldest))


@pytest.mark.asyncio
async def test_ensure_fixed_fetches_via_proxy(tmp_path, monkeypatch):
    storage = FakeStorage(str(tmp_path))
    calls = _patch_ok(monkeypatch)
    fetched = []

    class Proxy:
        async def fetch_to_temp(self, url, workers=4, chunk_size=65536):
            fetched.append((url, workers))
            path = os.path.join(str(tmp_path), "src.bin")
            with open(path, "wb") as fh:
                fh.write(b"SRC")
            return path

    out = await ensure_fixed_source(
        storage, "yt:abc", _src(), "mp3", stream_proxy=Proxy(), workers=6,
    )
    assert out is not None
    assert fetched == [("https://x/y", 6)]
    assert calls[0][1].endswith("src.bin")


@pytest.mark.asyncio
async def test_stream_route_sets_inline_disposition(client, created_key):
    r = await client.get("/stream/sample-001.mp3",
                         params={"key": created_key["api_key"]})
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    assert cd.startswith("inline") and ".mp3" in cd
