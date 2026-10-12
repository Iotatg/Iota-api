"""Tests for the user library API: playlists, import, favourites,
history, queue, top tracks, ratings, tags and overview."""
from __future__ import annotations

import os

import pytest

TEST_ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


# ── helpers ────────────────────────────────────────────────


async def _make_playlist(client, headers, name="Test List") -> int:
    r = await client.post(
        "/api/v1/library/playlists", json={"name": name}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _add_track(client, headers, playlist_id, media_id, **fields) -> int:
    payload = {"media_id": media_id}
    payload.update(fields)
    r = await client.post(
        f"/api/v1/library/playlists/{playlist_id}/tracks",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


TRACK = {"title": "Song", "artist": "Artist", "duration_seconds": 60}


# ── auth ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_library_requires_auth(client):
    r = await client.get("/api/v1/library/playlists")
    assert r.status_code == 401
    r2 = await client.post(
        "/api/v1/library/playlists", json={"name": "X"}
    )
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_library_auth_via_query_param(client, created_key):
    r = await client.get(
        "/api/v1/library/playlists", params={"key": created_key["api_key"]}
    )
    assert r.status_code == 200
    assert r.json() == []


# ── playlists CRUD ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_playlist_crud(client, auth_headers):
    pid = await _make_playlist(client, auth_headers, "Road Trip")
    # get
    r = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Road Trip"
    assert r.json()["track_count"] == 0
    assert r.json()["tracks"] == []
    # update
    r2 = await client.patch(
        f"/api/v1/library/playlists/{pid}",
        json={"name": "Road Trip 2", "description": "driving", "is_public": True},
        headers=auth_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "Road Trip 2"
    assert r2.json()["description"] == "driving"
    assert r2.json()["is_public"] is True
    # delete
    r3 = await client.delete(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert r3.status_code == 200
    r4 = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert r4.status_code == 404


@pytest.mark.asyncio
async def test_list_playlists(client, auth_headers):
    await _make_playlist(client, auth_headers, "A")
    await _make_playlist(client, auth_headers, "B")
    r = await client.get("/api/v1/library/playlists", headers=auth_headers)
    assert r.status_code == 200
    names = {p["name"] for p in r.json()}
    assert names == {"A", "B"}


@pytest.mark.asyncio
async def test_add_and_remove_playlist_track(client, auth_headers):
    pid = await _make_playlist(client, auth_headers)
    tid = await _add_track(
        client, auth_headers, pid, "sample-001.mp3", **TRACK
    )
    detail = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert detail.json()["track_count"] == 1
    assert detail.json()["tracks"][0]["media_id"] == "sample-001.mp3"
    assert detail.json()["tracks"][0]["position"] == 0
    # remove
    r = await client.delete(
        f"/api/v1/library/playlists/{pid}/tracks/{tid}", headers=auth_headers
    )
    assert r.status_code == 200
    detail2 = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert detail2.json()["track_count"] == 0


@pytest.mark.asyncio
async def test_add_duplicate_track_idempotent(client, auth_headers):
    pid = await _make_playlist(client, auth_headers)
    payload = {"media_id": "sample-001.mp3", **TRACK}
    r1 = await client.post(
        f"/api/v1/library/playlists/{pid}/tracks", json=payload, headers=auth_headers
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/library/playlists/{pid}/tracks", json=payload, headers=auth_headers
    )
    assert r2.status_code == 201  # idempotent
    detail = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert detail.json()["track_count"] == 1
    assert len(detail.json()["tracks"]) == 1


@pytest.mark.asyncio
async def test_add_track_enriches_from_provider(client, auth_headers):
    """Bare media_id with no display fields is enriched via the provider."""
    pid = await _make_playlist(client, auth_headers)
    r = await client.post(
        f"/api/v1/library/playlists/{pid}/tracks",
        json={"media_id": "sample-001.mp3"},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Sample One"
    assert body["artist"] == "Test Artist"
    assert body["duration_seconds"] == 60


@pytest.mark.asyncio
async def test_reorder_playlist_tracks(client, auth_headers):
    pid = await _make_playlist(client, auth_headers)
    ids = [
        await _add_track(client, auth_headers, pid, mid, **TRACK)
        for mid in ("sample-001.mp3", "sample-002.mp3", "sample-003.mp3")
    ]
    r = await client.post(
        f"/api/v1/library/playlists/{pid}/tracks/reorder",
        json={"ids": list(reversed(ids))},
        headers=auth_headers,
    )
    assert r.status_code == 200
    detail = await client.get(f"/api/v1/library/playlists/{pid}", headers=auth_headers)
    assert [t["media_id"] for t in detail.json()["tracks"]] == [
        "sample-003.mp3", "sample-002.mp3", "sample-001.mp3"
    ]
    # invalid: must list every track exactly once
    r2 = await client.post(
        f"/api/v1/library/playlists/{pid}/tracks/reorder",
        json={"ids": [ids[0]]},
        headers=auth_headers,
    )
    assert r2.status_code == 400


# ── playlist import ────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_youtube_playlist(client, auth_headers, monkeypatch):
    async def fake_fetch(url):
        return "My YT Playlist", [
            {"media_id": "yt:abc123", "title": "Song A", "artist": "Artist A"},
            {"media_id": "yt:def456", "title": "Song B", "artist": None},
        ]

    monkeypatch.setattr("app.services.library.fetch_youtube_playlist", fake_fetch)
    r = await client.post(
        "/api/v1/library/import",
        json={"url": "https://www.youtube.com/playlist?list=PLxxx"},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "My YT Playlist"
    assert body["track_count"] == 2
    assert [t["media_id"] for t in body["tracks"]] == ["yt:abc123", "yt:def456"]
    assert body["tracks"][0]["title"] == "Song A"
    assert body["tracks"][0]["artist"] == "Artist A"


@pytest.mark.asyncio
async def test_import_unsupported_url(client, auth_headers):
    r = await client.post(
        "/api/v1/library/import",
        json={"url": "https://example.com/playlist/123"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert r.json()["error"] == "import_failed"


@pytest.mark.asyncio
async def test_import_spotify_without_credentials(client, auth_headers):
    r = await client.post(
        "/api/v1/library/import",
        json={"url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert r.json()["error"] == "import_failed"


# ── favourites ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_favourites(client, auth_headers):
    mid = "sample-001.mp3"
    payload = {"media_id": mid, **TRACK}
    c0 = await client.get(
        "/api/v1/library/favourites/check", params={"media_id": mid}, headers=auth_headers
    )
    assert c0.json()["is_favourite"] is False
    r = await client.post("/api/v1/library/favourites", json=payload, headers=auth_headers)
    assert r.status_code == 201
    c1 = await client.get(
        "/api/v1/library/favourites/check", params={"media_id": mid}, headers=auth_headers
    )
    assert c1.json()["is_favourite"] is True
    # idempotent
    r2 = await client.post("/api/v1/library/favourites", json=payload, headers=auth_headers)
    assert r2.status_code == 201
    lst = await client.get("/api/v1/library/favourites", headers=auth_headers)
    assert len(lst.json()) == 1
    # remove
    d = await client.delete(f"/api/v1/library/favourites/{mid}", headers=auth_headers)
    assert d.status_code == 200
    lst2 = await client.get("/api/v1/library/favourites", headers=auth_headers)
    assert lst2.json() == []
    # remove again -> 404
    d2 = await client.delete(f"/api/v1/library/favourites/{mid}", headers=auth_headers)
    assert d2.status_code == 404


# ── history + top tracks ───────────────────────────────────


@pytest.mark.asyncio
async def test_history_and_top_tracks(client, auth_headers):
    for _ in range(3):
        await client.post(
            "/api/v1/library/history",
            json={"media_id": "sample-001.mp3", **TRACK},
            headers=auth_headers,
        )
    await client.post(
        "/api/v1/library/history",
        json={"media_id": "sample-002.mp3", **TRACK},
        headers=auth_headers,
    )
    # top tracks ordered by play count
    r = await client.get("/api/v1/library/top-tracks", headers=auth_headers)
    assert r.status_code == 200
    top = r.json()
    assert top[0]["media_id"] == "sample-001.mp3"
    assert top[0]["play_count"] == 3
    assert top[1]["play_count"] == 1
    # list history (newest first)
    h = await client.get("/api/v1/library/history", headers=auth_headers)
    assert len(h.json()) == 4
    # clear
    c = await client.delete("/api/v1/library/history", headers=auth_headers)
    assert c.json()["cleared"] == 4
    h2 = await client.get("/api/v1/library/history", headers=auth_headers)
    assert h2.json() == []


# ── queue ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_queue(client, auth_headers):
    r = await client.post(
        "/api/v1/library/queue",
        json={"media_id": "sample-001.mp3", **TRACK},
        headers=auth_headers,
    )
    assert r.status_code == 201
    item_id = r.json()["id"]
    r2 = await client.post(
        "/api/v1/library/queue",
        json={"media_id": "sample-002.mp3", **TRACK},
        headers=auth_headers,
    )
    item2_id = r2.json()["id"]
    q = await client.get("/api/v1/library/queue", headers=auth_headers)
    assert len(q.json()) == 2
    assert q.json()[0]["position"] == 0
    assert q.json()[1]["position"] == 1
    # reorder (swap)
    ro = await client.post(
        "/api/v1/library/queue/reorder",
        json={"ids": [item2_id, item_id]},
        headers=auth_headers,
    )
    assert ro.status_code == 200
    q2 = await client.get("/api/v1/library/queue", headers=auth_headers)
    assert q2.json()[0]["media_id"] == "sample-002.mp3"
    # remove
    d = await client.delete(f"/api/v1/library/queue/{item_id}", headers=auth_headers)
    assert d.status_code == 200
    # clear
    c = await client.delete("/api/v1/library/queue", headers=auth_headers)
    assert c.status_code == 200
    q3 = await client.get("/api/v1/library/queue", headers=auth_headers)
    assert q3.json() == []


@pytest.mark.asyncio
async def test_queue_reorder_invalid(client, auth_headers):
    await client.post(
        "/api/v1/library/queue",
        json={"media_id": "sample-001.mp3", **TRACK},
        headers=auth_headers,
    )
    # a non-existent id does not cover the queue exactly once
    r = await client.post(
        "/api/v1/library/queue/reorder", json={"ids": [999999]}, headers=auth_headers
    )
    assert r.status_code == 400


# ── ratings ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ratings(client, auth_headers):
    mid = "sample-001.mp3"
    g = await client.get(f"/api/v1/library/ratings/{mid}", headers=auth_headers)
    assert g.status_code == 404
    r = await client.put(
        f"/api/v1/library/ratings/{mid}", json={"rating": 4}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["rating"] == 4
    # update (upsert)
    r2 = await client.put(
        f"/api/v1/library/ratings/{mid}", json={"rating": 5}, headers=auth_headers
    )
    assert r2.json()["rating"] == 5
    # out of range
    r3 = await client.put(
        f"/api/v1/library/ratings/{mid}", json={"rating": 9}, headers=auth_headers
    )
    assert r3.status_code == 422
    # remove
    d = await client.delete(f"/api/v1/library/ratings/{mid}", headers=auth_headers)
    assert d.status_code == 200
    g2 = await client.get(f"/api/v1/library/ratings/{mid}", headers=auth_headers)
    assert g2.status_code == 404


# ── tags ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tags(client, auth_headers):
    mid = "sample-001.mp3"
    r = await client.post(
        f"/api/v1/library/tags?media_id={mid}",
        json={"tag": "Chill"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["tag"] == "chill"  # lowercased
    # list media tags
    t = await client.get(f"/api/v1/library/media/{mid}/tags", headers=auth_headers)
    assert t.json() == ["chill"]
    # tracks by tag
    tb = await client.get("/api/v1/library/tags/chill", headers=auth_headers)
    assert len(tb.json()) == 1
    # all tags
    a = await client.get("/api/v1/library/tags", headers=auth_headers)
    assert a.json() == ["chill"]
    # remove
    d = await client.delete(f"/api/v1/library/tags/{mid}/chill", headers=auth_headers)
    assert d.status_code == 200
    t2 = await client.get(f"/api/v1/library/media/{mid}/tags", headers=auth_headers)
    assert t2.json() == []


# ── overview ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overview(client, auth_headers):
    r = await client.get("/api/v1/library/overview", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    for k in ("playlists", "favourites", "history", "queue", "ratings", "tags"):
        assert k in body
    await _make_playlist(client, auth_headers, "O")
    r2 = await client.get("/api/v1/library/overview", headers=auth_headers)
    assert r2.json()["playlists"] == body["playlists"] + 1


# ── per-key scoping ────────────────────────────────────────


@pytest.mark.asyncio
async def test_library_scoped_per_key(client, created_key):
    # second key
    resp = await client.post(
        "/admin/keys",
        json={"name": "second"},
        headers={"X-Admin-Token": TEST_ADMIN_TOKEN},
    )
    assert resp.status_code == 201, resp.text
    second_headers = {"X-API-Key": resp.json()["api_key"]}
    first_headers = {"X-API-Key": created_key["api_key"]}
    # key1 adds a favourite
    r1 = await client.post(
        "/api/v1/library/favourites",
        json={"media_id": "sample-001.mp3", **TRACK},
        headers=first_headers,
    )
    assert r1.status_code == 201
    # key2 sees empty
    r2 = await client.get("/api/v1/library/favourites", headers=second_headers)
    assert r2.status_code == 200
    assert r2.json() == []
    # key1 sees its own
    r3 = await client.get("/api/v1/library/favourites", headers=first_headers)
    assert len(r3.json()) == 1
    # key2 cannot remove key1's favourite
    r4 = await client.delete(
        "/api/v1/library/favourites/sample-001.mp3", headers=second_headers
    )
    assert r4.status_code == 404
