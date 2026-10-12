"""Test admin endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_key_requires_admin_token(client):
    r = await client.post("/admin/keys", json={"name": "noauth"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_key_with_admin_token(client):
    r = await client.post(
        "/admin/keys",
        json={"name": "my-key"},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "my-key"
    assert body["api_key"].startswith("iota_")
    assert len(body["api_key"]) > 40  # prefix + 64 hex


@pytest.mark.asyncio
async def test_list_keys(client):
    r1 = await client.post(
        "/admin/keys",
        json={"name": "k1"},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    r2 = await client.post(
        "/admin/keys",
        json={"name": "k2"},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201

    r = await client.get(
        "/admin/keys",
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 2
    # Plaintext is NEVER returned by list endpoint
    for k in body:
        assert "api_key" not in k
        assert "key_hash" not in k


@pytest.mark.asyncio
async def test_get_key_by_id(client, created_key):
    r = await client.get(
        f"/admin/keys/{created_key['id']}",
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created_key["id"]
    assert body["name"] == created_key["name"]
    assert "api_key" not in body


@pytest.mark.asyncio
async def test_delete_key_disables(client, created_key):
    r = await client.delete(
        f"/admin/keys/{created_key['id']}",
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 204

    # Now the key should fail
    r2 = await client.get(
        "/info/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r2.status_code == 403
    assert r2.json()["error"] == "key_disabled"


@pytest.mark.asyncio
async def test_admin_stats(client, created_key):
    r = await client.get(
        "/admin/stats",
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 200
    body = r.json()
    assert "api_keys_total" in body
    assert "api_keys_active" in body
    assert "requests_today" in body
