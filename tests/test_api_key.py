"""Test API key validation."""
import pytest


@pytest.mark.asyncio
async def test_missing_key_returns_401(client, app_instance):
    r = await client.get("/info/sample-001.mp3")
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == "missing_api_key"


@pytest.mark.asyncio
async def test_invalid_key_returns_401(client, app_instance):
    r = await client.get("/info/sample-001.mp3", params={"key": "iota_" + "0" * 64})
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_wrong_prefix_returns_401(client, app_instance):
    r = await client.get("/info/sample-001.mp3", params={"key": "wrong_" + "0" * 32})
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_expired_key_returns_403(client, app_instance):
    from datetime import datetime, timedelta, timezone
    from app.config import hash_api_key
    from app.models.api_key import APIKey, APIKeyTier
    from app.database import AsyncSessionLocal

    digest = hash_api_key("iota_test_expired_key_aaaaaaaaaaaaaaaaaaaaaa")
    async with AsyncSessionLocal() as s:
        k = APIKey(
            name="expired",
            key_hash=digest,
            tier=APIKeyTier.FREE,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        s.add(k)
        await s.commit()

    r = await client.get("/info/sample-001.mp3", params={"key": "iota_test_expired_key_aaaaaaaaaaaaaaaaaaaaaa"})
    assert r.status_code == 403
    assert r.json()["error"] == "key_disabled"


@pytest.mark.asyncio
async def test_disabled_key_returns_403(client, app_instance):
    from app.config import hash_api_key
    from app.models.api_key import APIKey, APIKeyTier
    from app.database import AsyncSessionLocal

    digest = hash_api_key("iota_disabled_test_key_bbbbbbbbbbbbbbbbbbbbbb")
    async with AsyncSessionLocal() as s:
        k = APIKey(
            name="disabled",
            key_hash=digest,
            tier=APIKeyTier.FREE,
            active=False,
        )
        s.add(k)
        await s.commit()

    r = await client.get("/info/sample-001.mp3", params={"key": "iota_disabled_test_key_bbbbbbbbbbbbbbbbbbbbbb"})
    assert r.status_code == 403
    assert r.json()["error"] == "key_disabled"


@pytest.mark.asyncio
async def test_valid_key_passes(client, created_key, app_instance):
    r = await client.get(
        "/info/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["media_id"] == "sample-001.mp3"
    assert body["title"] == "Sample One"


@pytest.mark.asyncio
async def test_key_via_header(client, created_key):
    r = await client.get(
        "/info/sample-001.mp3",
        headers={"X-API-Key": created_key["api_key"]},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_key_via_bearer_header(client, created_key):
    r = await client.get(
        "/info/sample-001.mp3",
        headers={"Authorization": "Bearer " + created_key["api_key"]},
    )
    assert r.status_code == 200
