"""Minimal Iota Python client for catalog + IotaDB."""
from __future__ import annotations

from typing import Any, Optional

import httpx


class IotaClient:
    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "Iota-Python-SDK/2.0.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def search(self, q: str, limit: int = 10) -> dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/search", params={"q": q, "limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json()

    def insert(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/api/v1/db/{collection}/insert",
            json=document,
            headers=self._headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def find(self, collection: str, query: Optional[dict[str, Any]] = None) -> Any:
        r = httpx.post(
            f"{self.base_url}/api/v1/db/{collection}/find",
            json=query or {},
            headers=self._headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
