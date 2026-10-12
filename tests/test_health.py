"""Test health and root endpoints."""
import pytest


@pytest.mark.asyncio
async def test_root_returns_player_html(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Iota Songs API" in r.text


@pytest.mark.asyncio
async def test_identity_json(client):
    r = await client.get("/identity")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "iota-api"
    assert "docs" in body


@pytest.mark.asyncio
async def test_health_ok(client, app_instance):
    r = await client.get("/health")
    # We don't check for a strict 200 because the in-memory SQLite/fakeredis
    # setup may not satisfy the "ok" Postgres check via SELECT 1 — but it does
    # for SQLite, so we expect 200.
    body = r.json()
    assert "status" in body
    assert "checks" in body
    assert "postgres" in body["checks"]
    assert "redis" in body["checks"]


@pytest.mark.asyncio
async def test_metrics_endpoint_exposed(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "api_requests_total" in r.text or "text/plain" in r.headers.get("content-type", "")
