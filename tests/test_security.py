"""Test security: secret redaction, no stack traces, etc."""
import pytest


@pytest.mark.asyncio
async def test_admin_token_never_in_logs(client, created_key, caplog):
    """The admin token should never appear in any log output, even when used."""
    import logging
    caplog.set_level(logging.INFO)
    r = await client.post(
        "/admin/keys",
        json={"name": "redact-test"},
        headers={"X-Admin-Token": "test_admin_token_" + "x" * 32},
    )
    assert r.status_code == 201
    full = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "test_admin_token_" not in full
    assert "xxx" not in full or "REDACTED" in full


@pytest.mark.asyncio
async def test_api_key_never_in_logs(client, created_key, caplog):
    """The plaintext API key should never appear in OUR app's logs.

    Note: httpx's own debug logger will print full URLs; we only inspect
    records that came from our own loggers.
    """
    import logging
    caplog.set_level(logging.INFO)
    # Silence httpx so its URL-debug logs don't pollute the test
    logging.getLogger("httpx").setLevel(logging.WARNING)
    r = await client.get(
        "/info/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    # Filter to our own loggers
    our_records = [r for r in caplog.records if r.name.startswith("app.")]
    full = "\n".join(rec.getMessage() for rec in our_records)
    assert created_key["api_key"] not in full, (
        f"API key leaked into app logs: {full!r}"
    )


@pytest.mark.asyncio
async def test_error_response_no_stack_trace(client, created_key):
    r = await client.get(
        "/stream/does-not-exist.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 404
    body = r.json()
    assert "Traceback" not in str(body)
    assert "error" in body
    assert "detail" in body


@pytest.mark.asyncio
async def test_security_headers_present(client, app_instance):
    r = await client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "no-referrer"


@pytest.mark.asyncio
async def test_request_id_in_response(client):
    r = await client.get("/health")
    assert "x-request-id" in r.headers
    # Should be a 32-char hex
    assert len(r.headers["x-request-id"]) >= 16
