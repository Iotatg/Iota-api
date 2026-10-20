"""Tests for the litterbox self-heal mirror store."""
from __future__ import annotations

import json

import pytest

from app.services import mirror_store


@pytest.fixture(autouse=True)
def isolated_index(monkeypatch, tmp_path):
    monkeypatch.setattr(mirror_store, "_entries", None)
    monkeypatch.setattr(mirror_store, "_INDEX_PATH", tmp_path / "mirror_index.json")
    monkeypatch.setenv("IOTA_MIRROR", "1")
    yield


def _seed(vid="AAAAAAAAAAA", url="https://litter.catbox.moe/q3fge5.mp3",
          mime="audio/mpeg", ttl=7200, kind="audio"):
    table = mirror_store._load()
    import time
    table[vid] = {"url": url, "kind": kind, "mime": mime, "size": 10,
                  "expires_at": time.time() + ttl}
    return table


def test_enabled_toggle(monkeypatch):
    assert mirror_store.is_enabled() is True
    monkeypatch.setenv("IOTA_MIRROR", "0")
    assert mirror_store.is_enabled() is False
    assert mirror_store.entry_for("yt:AAAAAAAAAAA", "audio") is None


def test_video_id_extraction():
    assert mirror_store._video_id("yt:AAAAAAAAAAA") == "AAAAAAAAAAA"
    assert mirror_store._video_id("AAAAAAAAAAA") == "AAAAAAAAAAA"
    assert mirror_store._video_id("dz:584703592") == ""
    assert mirror_store._video_id("yt:short") == ""


def test_entry_for_respects_expiry_and_safety_margin():
    _seed(ttl=mirror_store._SAFETY_MARGIN + 60)
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio") is not None
    _seed(ttl=mirror_store._SAFETY_MARGIN - 60)
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio") is None


def test_entry_for_kind_mismatch():
    _seed()
    assert mirror_store.entry_for("AAAAAAAAAAA", "video") is None
    _seed(url="https://litter.catbox.moe/x9zz1.mp4", mime="video/mp4", kind="video")
    assert mirror_store.entry_for("AAAAAAAAAAA", "video") is not None


def test_stream_source_shape():
    _seed()
    src = mirror_store.stream_source("yt:AAAAAAAAAAA", "audio")
    assert src is not None
    assert src.direct_url == "https://litter.catbox.moe/q3fge5.mp3"
    assert src.mime_type == "audio/mpeg"
    assert mirror_store.stream_source("dz:584703592", "audio") is None


def test_load_drops_expired_and_bad_urls(tmp_path, monkeypatch):
    import time
    path = tmp_path / "idx2.json"
    path.write_text(json.dumps({
        "AAAAAAAAAAA": {"url": "https://litter.catbox.moe/ok123.mp3", "mime": "audio/mpeg",
                        "expires_at": time.time() + 7200},
        "BBBBBBBBBBB": {"url": "http://evil.example/x.mp3", "mime": "audio/mpeg",
                        "expires_at": time.time() + 7200},
        "CCCCCCCCCCC": {"url": "https://litter.catbox.moe/old1.mp3", "mime": "audio/mpeg",
                        "expires_at": time.time() - 5},
        "bad!!": {"url": "https://litter.catbox.moe/xidok.mp3", "mime": "audio/mpeg",
                  "expires_at": time.time() + 7200},
    }), encoding="utf-8")
    monkeypatch.setattr(mirror_store, "_entries", None)
    monkeypatch.setattr(mirror_store, "_INDEX_PATH", path)
    table = mirror_store._load()
    assert set(table) == {"AAAAAAAAAAA"}


async def test_store_persists_validated_url(monkeypatch):
    captured = {}

    async def fake_upload(data, ext, mime):
        captured.update(data=data, ext=ext, mime=mime)
        return "https://litter.catbox.moe/abc123.m4a"

    monkeypatch.setattr(mirror_store, "_upload", fake_upload)
    await mirror_store._store("AAAAAAAAAAA", "audio", "audio/mp4", b"x" * 100)
    entry = mirror_store.entry_for("AAAAAAAAAAA", "audio")
    assert entry is not None
    assert entry["url"] == "https://litter.catbox.moe/abc123.m4a"
    assert captured["ext"] == "m4a"
    persisted = json.loads(
        mirror_store._INDEX_PATH.read_text(encoding="utf-8"))
    assert "AAAAAAAAAAA" in persisted


async def test_store_rejects_bad_upload_response(monkeypatch):
    async def fake_upload(data, ext, mime):
        return "https://evil.example.com/payload.mp3"

    monkeypatch.setattr(mirror_store, "_upload", fake_upload)
    await mirror_store._store("AAAAAAAAAAA", "audio", "audio/mpeg", b"x" * 10)
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio") is None


async def test_upload_failure_engages_backoff(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(mirror_store, "_cooldown_until", 0.0)

    async def fake_upload(data, ext, mime):
        calls.append(1)
        return None

    monkeypatch.setattr(mirror_store, "_upload", fake_upload)
    await mirror_store._store("AAAAAAAAAAA", "audio", "audio/mpeg", b"x" * 10)
    assert calls == [1]
    assert mirror_store._store_cooldown_active() is True
    # enqueue path must short-circuit while cooling down
    mirror_store.enqueue_mirror("BBBBBBBBBBB", "audio", "audio/mpeg", b"y" * 10)
    import asyncio as aio
    await aio.sleep(0.05)
    assert calls == [1]


async def test_store_skips_fresh_existing_entry(monkeypatch):
    calls = []

    async def fake_upload(data, ext, mime):
        calls.append(data)
        return "https://litter.catbox.moe/new99.mp3"

    monkeypatch.setattr(mirror_store, "_upload", fake_upload)
    _seed(ttl=7200)
    await mirror_store._store("AAAAAAAAAAA", "audio", "audio/mpeg", b"y" * 10)
    assert calls == []
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio")["url"] == \
        "https://litter.catbox.moe/q3fge5.mp3"


async def test_relay_tier_prefers_mirror_over_catalog(monkeypatch):
    from app.services.stream_fallback import relay_source

    class _FailingYt:
        name = "yt"

        async def rotation_stream(self, vid, kind="audio"):
            return None

    monkeypatch.setattr("app.services.stream_fallback.find_youtube_provider",
                        lambda p: _FailingYt())
    # no mirror yet -> falls through to the offline catalog tier
    monkeypatch.setattr("app.services.stream_fallback.mirror_store.stream_source",
                        lambda media_id, kind: None)
    async def fake_cached(vid, kind):
        return "CATALOG"

    monkeypatch.setattr("app.services.stream_fallback._cached_source", fake_cached)
    assert await relay_source("prov", "AAAAAAAAAAA", "audio") == "CATALOG"
    monkeypatch.undo()
    # the mirror is opt-in, undo() also dropped the env var of the fixture
    monkeypatch.setenv("IOTA_MIRROR", "1")
    _seed()
    hit = await relay_source("prov", "AAAAAAAAAAA", "audio")
    assert hit.direct_url == "https://litter.catbox.moe/q3fge5.mp3"


def test_invalidate_removes_and_persists():
    import os
    _seed()
    mirror_store.invalidate("AAAAAAAAAAA")
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio") is None
    mirror_store.invalidate("ZZZZZZZZZZZ")  # unknown id: no error
    # persisted state reflects removal
    mirror_store._entries = None
    assert mirror_store.entry_for("AAAAAAAAAAA", "audio") is None
