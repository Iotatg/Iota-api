"""Song inverted-index ranking, lookup, pagination, suggest."""
from __future__ import annotations

from app.catalog.index import SongIndex


SAMPLE = [
    {
        "video_id": "iotademo001",
        "title": "Neon Drift - Iota Radio",
        "artist": "Iota Ensemble",
        "stream_url": "/api/file/iotademo001",
        "source": "iota_cloud",
        "thumbnail": "/static/thumbs/default.svg",
        "duration_seconds": 180,
        "tags": ["electronic", "demo"],
    },
    {
        "video_id": "iotademo002",
        "title": "Midnight Circuit",
        "artist": "Violet Wave",
        "stream_url": "/api/file/iotademo002",
        "source": "iota_cloud",
        "thumbnail": "/static/thumbs/default.svg",
        "duration_seconds": 210,
        "tags": ["synth", "demo"],
    },
    {
        "video_id": "iotademo003",
        "title": "Iota Ensemble Live - Cyan Pulse",
        "artist": "Iota Ensemble",
        "stream_url": "/api/file/iotademo003",
        "source": "iota_cloud",
        "thumbnail": "/static/thumbs/default.svg",
        "duration_seconds": 240,
        "tags": ["live", "demo"],
    },
]


def test_exact_video_id_is_first_and_only():
    idx = SongIndex(SAMPLE)
    hits = idx.search("iotademo002", limit=10)
    assert len(hits) == 1
    assert hits[0]["video_id"] == "iotademo002"


def test_all_tokens_rank_above_partial():
    idx = SongIndex(SAMPLE)
    hits = idx.search("iota ensemble", limit=10)
    assert hits[0]["video_id"] in {"iotademo001", "iotademo003"}
    assert all("iota" in h["title"].lower() or "iota" in h["artist"].lower() for h in hits)


def test_title_substring_match():
    idx = SongIndex(SAMPLE)
    hits = idx.search("neon", limit=5)
    assert hits[0]["video_id"] == "iotademo001"


def test_empty_query_returns_empty():
    idx = SongIndex(SAMPLE)
    assert idx.search("   ", limit=5) == []


def test_get_by_id_and_miss():
    idx = SongIndex(SAMPLE)
    assert idx.get("iotademo001")["title"].startswith("Neon")
    assert idx.get("missingxxxx") is None


def test_random_respects_limit_and_does_not_mutate():
    idx = SongIndex(SAMPLE)
    a = idx.random(2)
    b = idx.random(2)
    assert len(a) == 2
    assert len(b) == 2
    assert idx.get("iotademo001") is not None


def test_page_and_stats():
    idx = SongIndex(SAMPLE)
    page = idx.page(page=1, limit=2)
    assert page["total_songs"] == 3
    assert page["total_pages"] == 2
    assert len(page["results"]) == 2
    stats = idx.stats()
    assert stats["total_songs"] == 3
    assert stats["iota_cloud_songs"] == 3


def test_suggest_prefixes():
    idx = SongIndex(SAMPLE)
    suggestions = idx.suggest("neo", limit=5)
    assert any("Neon" in s for s in suggestions)


def test_search_is_order_independent_for_tokens():
    idx = SongIndex(SAMPLE)
    a = [h["video_id"] for h in idx.search("ensemble iota", limit=10)]
    b = [h["video_id"] for h in idx.search("iota ensemble", limit=10)]
    assert a == b
