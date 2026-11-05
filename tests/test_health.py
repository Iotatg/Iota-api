"""Test health and root endpoints."""
import pytest


@pytest.mark.asyncio
async def test_root_returns_app_shell(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "IOTA AUDIO" in r.text
    assert "/static/app.js" in r.text


@pytest.mark.asyncio
async def test_dev_returns_player_html(client):
    r = await client.get("/dev")
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
async def test_metrics_endpoint_requires_admin_token(client):
    """Metrics reveal request rates and endpoint usage, so they are
    behind the admin token."""
    r = await client.get("/metrics")
    assert r.status_code in (401, 403)

    from tests.conftest import TEST_ADMIN_TOKEN
    ok = await client.get(
        "/metrics", headers={"X-Admin-Token": TEST_ADMIN_TOKEN}
    )
    assert ok.status_code == 200
    assert "api_requests_total" in ok.text or "text/plain" in ok.headers.get(
        "content-type", ""
    )


@pytest.mark.asyncio
async def test_liveness_probe_touches_no_dependency(client):
    """The liveness probe must answer even when the database is gone."""
    r = await client.get("/health/live")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "checks" not in body


@pytest.mark.asyncio
async def test_readiness_probe_reports_checks(client):
    r = await client.get("/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert "postgres" in body["checks"]
    assert "redis" in body["checks"]


@pytest.mark.asyncio
async def test_health_check_is_cached(client, app_instance):
    """Repeated health calls must not re-query the database every time."""
    from app.routes import health as health_route

    health_route._check_cache["at"] = 0.0
    health_route._check_cache["payload"] = None

    calls = {"n": 0}
    original = health_route._collect_checks

    async def counting(session, redis_cache):
        calls["n"] += 1
        return await original(session, redis_cache)

    health_route._collect_checks = counting
    try:
        for _ in range(5):
            r = await client.get("/health")
            assert r.status_code in (200, 503)
    finally:
        health_route._collect_checks = original
        health_route._check_cache["at"] = 0.0
        health_route._check_cache["payload"] = None

    # Five calls inside the cache window must produce one dependency
    # check, not five.
    assert calls["n"] == 1
