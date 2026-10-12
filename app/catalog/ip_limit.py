"""Per-IP sliding window for the public catalog (no API key)."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request


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

    def remaining(self, request: Request) -> int:
        ip = self.client_ip(request)
        now = time.time()
        self.hits[ip] = [ts for ts in self.hits[ip] if now - ts < self.window]
        return max(0, self.rpm - len(self.hits[ip]))

    def check(self, request: Request) -> None:
        ip = self.client_ip(request)
        now = time.time()
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
