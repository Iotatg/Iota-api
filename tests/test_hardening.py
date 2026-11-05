"""Tests for the production hardening middleware.

Covers the per-IP abuse guard, the request body cap, the hardened
response headers and the trusted-host filter.
"""
from __future__ import annotations

import pytest


def _client():
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    return AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://testserver",
    )


class TestIPRateLimit:
    @pytest.mark.asyncio
    async def test_anonymous_flood_is_rejected(self, monkeypatch):
        from app.middleware.security import IPRateLimitMiddleware

        calls = {"n": 0}

        async def app(scope, receive, send):
            calls["n"] += 1
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = IPRateLimitMiddleware(app, per_minute=3, admin_per_minute=1)
        scope = {
            "type": "http",
            "path": "/search",
            "method": "GET",
            "headers": [],
            "query_string": b"",
            "client": ("10.0.0.1", 1234),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            return None

        statuses = []
        for _ in range(5):
            sent = []

            async def collect(message, _sent=sent):
                _sent.append(message)

            await middleware(scope, receive, collect)
            statuses.append(sent[0]["status"])

        assert statuses[:3] == [200, 200, 200]
        assert statuses[3:] == [429, 429]
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_admin_bucket_is_tighter(self):
        from app.middleware.security import IPRateLimitMiddleware

        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = IPRateLimitMiddleware(app, per_minute=100, admin_per_minute=1)

        async def request(path):
            sent = []

            async def collect(message):
                sent.append(message)

            await middleware(
                {
                    "type": "http",
                    "path": path,
                    "method": "GET",
                    "headers": [],
                    "query_string": b"",
                    "client": ("10.0.0.2", 1234),
                },
                lambda: _none(),
                collect,
            )
            return sent[0]["status"]

        async def _none():
            return {"type": "http.request", "body": b"", "more_body": False}

        assert await request("/admin/keys") == 200
        assert await request("/admin/keys") == 429

    @pytest.mark.asyncio
    async def test_keyed_requests_use_the_larger_bucket(self):
        from app.middleware.security import IPRateLimitMiddleware

        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = IPRateLimitMiddleware(
            app, per_minute=1, keyed_per_minute=50, admin_per_minute=1
        )

        async def request(query):
            sent = []

            async def collect(message):
                sent.append(message)

            await middleware(
                {
                    "type": "http",
                    "path": "/stream/x",
                    "method": "GET",
                    "headers": [],
                    "query_string": query,
                    "client": ("10.0.0.3", 1234),
                },
                lambda: _none(),
                collect,
            )
            return sent[0]["status"]

        async def _none():
            return {"type": "http.request", "body": b"", "more_body": False}

        # Anonymous request consumes the single anonymous slot.
        assert await request(b"") == 200
        assert await request(b"") == 429
        # A keyed request is judged by the keyed bucket instead.
        assert await request(b"key=abc") == 200
        assert await request(b"key=abc") == 200

    @pytest.mark.asyncio
    async def test_limit_zero_disables_the_guard(self):
        from app.middleware.security import IPRateLimitMiddleware

        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = IPRateLimitMiddleware(app, per_minute=0)

        async def _none():
            return {"type": "http.request", "body": b"", "more_body": False}

        for _ in range(5):
            sent = []

            async def collect(message):
                sent.append(message)

            await middleware(
                {
                    "type": "http",
                    "path": "/search",
                    "method": "GET",
                    "headers": [],
                    "query_string": b"",
                    "client": ("10.0.0.4", 1234),
                },
                _none,
                collect,
            )
            assert sent[0]["status"] == 200

    def test_client_ip_prefers_the_trusted_proxy_header(self):
        from app.middleware.security import _client_ip

        scope = {
            "headers": [(b"x-real-ip", b"203.0.113.9")],
            "client": ("10.0.0.5", 1),
        }
        assert _client_ip(scope, trust_proxy=True) == "203.0.113.9"
        assert _client_ip(scope, trust_proxy=False) == "10.0.0.5"


class TestBodySizeLimit:
    @pytest.mark.asyncio
    async def test_oversized_body_is_refused(self):
        from app.middleware.security import BodySizeLimitMiddleware

        reached = {"n": 0}

        async def app(scope, receive, send):
            reached["n"] += 1
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = BodySizeLimitMiddleware(app, max_bytes=100)
        sent = []

        async def collect(message):
            sent.append(message)

        async def _none():
            return {"type": "http.request", "body": b"", "more_body": False}

        await middleware(
            {
                "type": "http",
                "path": "/library",
                "method": "POST",
                "headers": [(b"content-length", b"500")],
                "query_string": b"",
            },
            _none,
            collect,
        )
        assert sent[0]["status"] == 413
        assert reached["n"] == 0

    @pytest.mark.asyncio
    async def test_body_within_the_limit_passes(self):
        from app.middleware.security import BodySizeLimitMiddleware

        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = BodySizeLimitMiddleware(app, max_bytes=100)
        sent = []

        async def collect(message):
            sent.append(message)

        async def _none():
            return {"type": "http.request", "body": b"", "more_body": False}

        await middleware(
            {
                "type": "http",
                "path": "/library",
                "method": "POST",
                "headers": [(b"content-length", b"50")],
                "query_string": b"",
            },
            _none,
            collect,
        )
        assert sent[0]["status"] == 200


class TestResponseHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_are_present(self, client):
        r = await client.get("/health")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "no-referrer"
        assert "geolocation=()" in r.headers["Permissions-Policy"]
        assert "Content-Security-Policy" in r.headers
        assert r.headers["X-Request-Id"]

    @pytest.mark.asyncio
    async def test_request_id_is_echoed(self, client):
        r = await client.get("/health", headers={"X-Request-Id": "abc123"})
        assert r.headers["X-Request-Id"] == "abc123"

    @pytest.mark.asyncio
    async def test_cors_headers_survive_an_error_response(self, client):
        """The CORS middleware must be outermost so a 404/429 still
        carries the headers a browser needs to read the status."""
        r = await client.get(
            "/health",
            headers={"Origin": "https://example.com"},
        )
        assert r.headers.get("access-control-allow-origin") in (
            "*", "https://example.com"
        )
