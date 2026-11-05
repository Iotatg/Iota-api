"""Production hardening middleware.

Everything here is implemented as pure ASGI rather than through
``BaseHTTPMiddleware``: the latter wraps every response in an extra
streaming generator, which costs real throughput once the API is serving
millions of requests. Pure ASGI keeps the per-request overhead to a
single pass over the response start message.

Three concerns:

- :class:`RequestContextMiddleware` — request id, timing, structured
  logging, Prometheus counters and the hardened response headers.
- :class:`BodySizeLimitMiddleware` — rejects oversized request bodies
  before a handler (or the database) ever sees them.
- :class:`IPRateLimitMiddleware` — per-IP abuse guard, with a much
  tighter bucket on the admin routes where a stolen token is the prize.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Awaitable, Callable, MutableMapping, Optional

from starlette.datastructures import MutableHeaders

from app.utils.logging import get_logger
from app.utils.metrics import api_requests_total

logger = get_logger(__name__)

Scope = MutableMapping
Receive = Callable[[], Awaitable[MutableMapping]]
Send = Callable[[MutableMapping], Awaitable[None]]

# Header names we look at, lower-cased bytes.
_API_KEY_HEADERS = (b"x-api-key", b"authorization")


def _header(scope: Scope, name: bytes) -> Optional[str]:
    for raw_name, raw_value in scope.get("headers", ()):
        if raw_name == name:
            try:
                return raw_value.decode("latin-1")
            except Exception:
                return None
    return None


def _client_ip(scope: Scope, trust_proxy: bool) -> str:
    """Best-effort client address.

    ``X-Real-IP`` is set (overwritten) by our own nginx edge, so it is
    the address nginx actually saw. The socket peer is used when the
    proxy header is not trusted, otherwise a client could spoof its
    address by sending the header itself.
    """
    if trust_proxy:
        real = _header(scope, b"x-real-ip")
        if real:
            candidate = real.strip().split(",")[0].strip()
            if candidate:
                return candidate
    client = scope.get("client")
    if client:
        return str(client[0])
    return "unknown"


def _has_api_key(scope: Scope) -> bool:
    """True when the caller presented a key (valid or not).

    Used to keep the anonymous bucket separate from the keyed one: a
    client with a key is governed by that key's own quota, while an
    anonymous caller is only allowed the public surface.
    """
    query = scope.get("query_string", b"").decode("latin-1", "ignore")
    if "key=" in query:
        return True
    for raw_name, _ in scope.get("headers", ()):
        if raw_name in _API_KEY_HEADERS:
            return True
    return False


class RequestContextMiddleware:
    """Request id, timing, logging, metrics and response headers."""

    def __init__(
        self,
        app,
        *,
        enable_hsts: bool = False,
        hsts_max_age: int = 31536000,
        expose_powered_by: bool = True,
        content_security_policy: Optional[str] = None,
    ) -> None:
        self.app = app
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.expose_powered_by = expose_powered_by
        self.content_security_policy = content_security_policy

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        rid = _header(scope, b"x-request-id") or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = rid
        started = time.perf_counter()
        state = {"status": 500, "responded": False}

        async def send_wrapper(message: MutableMapping) -> None:
            if message["type"] == "http.response.start":
                state["responded"] = True
                state["status"] = message.get("status", 500)
                elapsed_ms = (time.perf_counter() - started) * 1000
                headers = MutableHeaders(scope=message)
                headers["X-Request-Id"] = rid
                headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
                headers["X-Response-Time-MS"] = f"{elapsed_ms:.2f}ms"
                headers["X-API-Version"] = "2.0.0"
                if self.expose_powered_by:
                    headers["X-Powered-By"] = "Iota-Music-Engine"
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault(
                    "Permissions-Policy",
                    "geolocation=(), microphone=(), camera=(), payment=()",
                )
                headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
                headers.setdefault(
                    "Cross-Origin-Resource-Policy", "cross-origin"
                )
                if self.content_security_policy:
                    headers.setdefault(
                        "Content-Security-Policy", self.content_security_policy
                    )
                if self.enable_hsts:
                    headers.setdefault(
                        "Strict-Transport-Security",
                        f"max-age={self.hsts_max_age}; includeSubDomains",
                    )
                song_count = self._song_count(scope)
                if song_count is not None:
                    headers["X-Total-Songs"] = str(song_count)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.exception(
                "unhandled_error", extra={"request_id": rid, "err": str(exc)}
            )
            if state["responded"]:
                raise
            body = json.dumps({
                "error": "internal_error",
                "detail": "An internal error occurred.",
                "request_id": rid,
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"x-request-id", rid.encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
        finally:
            self._record(scope, state["status"], started)

    @staticmethod
    def _song_count(scope: Scope) -> Optional[int]:
        app = scope.get("app")
        index = getattr(getattr(app, "state", None), "song_index", None)
        if index is None:
            return None
        try:
            return len(index)
        except TypeError:
            return None

    @staticmethod
    def _record(scope: Scope, status: int, started: float) -> None:
        elapsed_ms = (time.perf_counter() - started) * 1000
        route = scope.get("route")
        endpoint = getattr(route, "path", None) or scope.get("path", "unknown")
        method = scope.get("method", "GET")
        try:
            api_requests_total.labels(
                endpoint=endpoint, method=method, status=str(status)
            ).inc()
        except Exception:
            pass
        logger.info("request", extra={
            "request_id": scope.get("state", {}).get("request_id"),
            "method": method,
            "path": scope.get("path", ""),
            "status": status,
            "duration_ms": elapsed_ms,
        })


class BodySizeLimitMiddleware:
    """Reject request bodies larger than the configured cap.

    The cap is checked from the ``Content-Length`` header, so an
    oversized upload is refused before it is read into memory or
    written to the database.
    """

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or self.max_bytes <= 0:
            await self.app(scope, receive, send)
            return
        raw_length = _header(scope, b"content-length")
        if raw_length:
            try:
                length = int(raw_length)
            except ValueError:
                length = -1
            if length > self.max_bytes:
                body = json.dumps({
                    "error": "payload_too_large",
                    "detail": (
                        f"Request body exceeds the {self.max_bytes} byte limit."
                    ),
                }).encode()
                await send({
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


class IPRateLimitMiddleware:
    """Per-IP abuse guard.

    Two buckets share one counter store:

    - anonymous callers get ``per_minute`` requests per minute,
    - callers that present an API key get ``keyed_per_minute``,
    - ``/admin`` always gets the tight ``admin_per_minute`` bucket.

    The counter store is Redis when the deployment has it (so the limit
    is global across replicas) and an in-process dictionary otherwise.
    """

    def __init__(
        self,
        app,
        *,
        per_minute: int = 600,
        keyed_per_minute: int = 6000,
        admin_per_minute: int = 20,
        window_seconds: int = 60,
        trust_proxy: bool = True,
    ) -> None:
        self.app = app
        self.per_minute = max(0, per_minute)
        self.keyed_per_minute = max(0, keyed_per_minute)
        self.admin_per_minute = max(0, admin_per_minute)
        self.window_seconds = max(1, window_seconds)
        self.trust_proxy = trust_proxy
        self._local: dict[tuple[str, str], int] = {}
        self._local_window = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_admin = path.startswith("/admin")
        if is_admin:
            limit = self.admin_per_minute
        elif _has_api_key(scope):
            limit = self.keyed_per_minute
        else:
            limit = self.per_minute
        if limit <= 0:
            await self.app(scope, receive, send)
            return

        ip = _client_ip(scope, self.trust_proxy)
        bucket = "admin" if is_admin else "api"
        count = await self._increment(scope, ip, bucket)
        if count > limit:
            retry_after = self.window_seconds
            body = json.dumps({
                "error": "rate_limited",
                "detail": "Too many requests from this address.",
                "retry_after_seconds": retry_after,
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(retry_after).encode()),
                    (b"x-ratelimit-limit", str(limit).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)

    async def _increment(self, scope: Scope, ip: str, bucket: str) -> int:
        window = int(time.time() // self.window_seconds)
        redis_client = self._redis(scope)
        if redis_client is not None:
            key = f"iota:iplimit:{bucket}:{window}:{ip}"
            try:
                count = await redis_client.incr(key)
                if count == 1:
                    await redis_client.expire(key, self.window_seconds * 2)
                return int(count)
            except Exception:
                logger.warning("ip_rate_limit_redis_failed", extra={"ip": ip})
        return self._increment_local(ip, bucket, window)

    @staticmethod
    def _redis(scope: Scope):
        app = scope.get("app")
        return getattr(getattr(app, "state", None), "redis", None)

    def _increment_local(self, ip: str, bucket: str, window: int) -> int:
        if window != self._local_window:
            self._local.clear()
            self._local_window = window
        key = (bucket, ip)
        count = self._local.get(key, 0) + 1
        self._local[key] = count
        return count
