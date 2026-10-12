"""Tests for the persistent stream-URL cache service (SQLite-backed)."""
from __future__ import annotations

from app.services.media_provider import MediaMetadata
from app.services.stream_cache import StreamCacheService


def _meta(media_id: str, title: str = "T") -> MediaMetadata:
    return MediaMetadata(
        media_id=media_id,
        title=title,
        artist="Artist",
        duration_seconds=213,
        mime_type="audio/mpeg",
        provider="yt",
    )


async def test_put_and_get(app_instance):
    svc = StreamCacheService(ttl=3600)
    await svc.put(
        "dQw4w9WgXcQ", "https://cdn.up.test/a.mp3?sig=abc",
        _meta("dQw4w9WgXcQ", "Rick Roll"),
    )
    hit = await svc.get("dQw4w9WgXcQ")
    assert hit is not None
    url, meta = hit
    assert url == "https://cdn.up.test/a.mp3?sig=abc"
    assert meta.title == "Rick Roll"
    assert meta.artist == "Artist"
    assert meta.duration_seconds == 213


async def test_get_missing_returns_none(app_instance):
    svc = StreamCacheService(ttl=3600)
    assert await svc.get("H5dObFvq9VU") is None


async def test_invalidate_removes_entry(app_instance):
    svc = StreamCacheService(ttl=3600)
    await svc.put("dQw4w9WgXcQ", "https://cdn.up.test/a.mp3", _meta("dQw4w9WgXcQ"))
    await svc.invalidate("dQw4w9WgXcQ")
    assert await svc.get("dQw4w9WgXcQ") is None


async def test_expired_entry_not_returned(app_instance):
    svc = StreamCacheService(ttl=3600)
    # Negative TTL => already expired at write time.
    await svc.put("dQw4w9WgXcQ", "https://cdn.up.test/a.mp3", _meta("dQw4w9WgXcQ"), ttl=-1)
    assert await svc.get("dQw4w9WgXcQ") is None


async def test_purge_expired_keeps_live(app_instance):
    svc = StreamCacheService(ttl=3600)
    await svc.put("dQw4w9WgXcQ", "https://cdn.up.test/a.mp3", _meta("dQw4w9WgXcQ"), ttl=-1)
    await svc.put("H5dObFvq9VU", "https://cdn.up.test/b.mp3", _meta("H5dObFvq9VU"), ttl=3600)
    removed = await svc.purge_expired()
    assert removed >= 1
    assert await svc.get("dQw4w9WgXcQ") is None
    assert await svc.get("H5dObFvq9VU") is not None
