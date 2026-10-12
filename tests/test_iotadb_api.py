"""IotaDB HTTP API: sandbox key, CRUD, isolation."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sandbox_insert_find_update_delete(client):
    created = await client.post(
        "/api/v1/db/posts/insert",
        json={"title": "Hello Iota", "likes": 3},
    )
    assert created.status_code == 200
    doc = created.json()
    assert doc["title"] == "Hello Iota"
    doc_id = doc["id"]

    found = await client.post("/api/v1/db/posts/find", json={"likes": {"$gte": 3}})
    assert found.status_code == 200
    assert any(item["id"] == doc_id for item in found.json())

    updated = await client.put(f"/api/v1/db/posts/{doc_id}", json={"likes": 9})
    assert updated.status_code == 200
    assert updated.json()["likes"] == 9

    got = await client.get(f"/api/v1/db/posts/{doc_id}")
    assert got.status_code == 200
    assert got.json()["likes"] == 9

    deleted = await client.delete(f"/api/v1/db/posts/{doc_id}")
    assert deleted.status_code == 200
    missing = await client.get(f"/api/v1/db/posts/{doc_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_anonymous_key_and_aggregate(client):
    key_resp = await client.post("/api/v1/keys/anonymous")
    assert key_resp.status_code == 200
    raw = key_resp.json()["raw_key"]
    assert raw.startswith("iota_live_")
    headers = {"X-API-Key": raw}
    await client.post("/api/v1/db/scores/insert", json={"name": "a", "score": 10}, headers=headers)
    await client.post("/api/v1/db/scores/insert", json={"name": "b", "score": 90}, headers=headers)
    agg = await client.post(
        "/api/v1/db/scores/aggregate",
        json={"pipeline": [{"$match": {"score": {"$gte": 50}}}, {"$count": "n"}]},
        headers=headers,
    )
    assert agg.status_code == 200
    assert agg.json() == [{"n": 1}]


@pytest.mark.asyncio
async def test_lookup_rejects_injection_stage(client):
    r = await client.post(
        "/api/v1/db/posts/aggregate",
        json={"pipeline": [{"$lookup": {"from": "users"}}]},
    )
    assert r.status_code == 400
