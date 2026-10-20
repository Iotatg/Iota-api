"""Per-IP sliding window for the public catalog (no API key).

Every public route shares one limiter, so ``IOTA_PUBLIC_RPM`` is the real
limit of the service and not the limit per route.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request

# The number of IP addresses that are kept in memory at the same time.
MAX_TRACKED_IPS = 4096


class IpSlidingWindow:
    def __init__(self, requests_per_minute: int = 60) -> None:
        self.rpm = requests_per_minute
        self.window = 60
        self.hits: dict[str, list[float]] = defaultdict(list)

    def client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "127.0.0.1"

    def _prune(self, now: float) -> None:
        """Drop the hits that fell out of the window."""
        for ip in list(self.hits):
            fresh = [ts for ts in self.hits[ip] if now - ts < self.window]
            if fresh:
                self.hits[ip] = fresh
            else:
                self.hits.pop(ip, None)

    def remaining(self, request: Request) -> int:
        ip = self.client_ip(request)
        now = time.time()
        self.hits[ip] = [ts for ts in self.hits[ip] if now - ts < self.window]
        return max(0, self.rpm - len(self.hits[ip]))

    def check(self, request: Request) -> None:
        ip = self.client_ip(request)
        now = time.time()
        if len(self.hits) > MAX_TRACKED_IPS:
            self._prune(now)
            if len(self.hits) > MAX_TRACKED_IPS:
                # Still too many, forget the oldest half of them.
                oldest = sorted(self.hits, key=lambda key: self.hits[key][0])[
                    : len(self.hits) - MAX_TRACKED_IPS // 2
                ]
                for stale in oldest:
                    self.hits.pop(stale, None)
        self.hits[ip] = [ts for ts in self.hits[ip] if now - ts < self.window]
        if len(self.hits[ip]) >= self.rpm:
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error": "Too Many Requests",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded (Max {self.rpm} requests/min).",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )
        self.hits[ip].append(now)


_limiter: IpSlidingWindow | None = None


def public_limiter() -> IpSlidingWindow | None:
    """The limiter of the public routes, or None when the limit is disabled.

    0 requests per minute disables the limit entirely, override with
    IOTA_PUBLIC_RPM=<requests per minute> to re-enable it.
    """
    global _limiter
    if _limiter is None:
        rpm = int(os.environ.get("IOTA_PUBLIC_RPM", "0"))
        _limiter = IpSlidingWindow(rpm) if rpm > 0 else None
    return _limiter
