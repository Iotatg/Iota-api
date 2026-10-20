"""API key authentication.

Validates the `key` query parameter, X-API-Key header, or
`Authorization: Bearer` against the `api_keys` table. Returns a hydrated
APIKey row on success, raises HTTPException on failure.

Keys are looked up by SHA-256 hash, not by plaintext.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, hash_api_key
from app.database import get_session
from app.models.api_key import APIKey
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Where to look for the key: query param first, then header.
QUERY_PARAM = "key"
HEADER_NAME = "X-API-Key"


async def lookup_key(plaintext: str, session: AsyncSession) -> Optional[APIKey]:
    """Look up an API key by its SHA-256 hash."""
    if not plaintext:
        return None
    digest = hash_api_key(plaintext)
    result = await session.execute(
        select(APIKey).where(APIKey.key_hash == digest)
    )
    return result.scalar_one_or_none()


def extract_key_from_request(request: Request) -> Optional[str]:
    """Pull the key from the `key` query param, `X-API-Key`, or
    `Authorization: Bearer` header, in that order."""
    v = request.query_params.get(QUERY_PARAM)
    if v:
        return v.strip() or None
    h = request.headers.get(HEADER_NAME)
    if h:
        return h.strip() or None
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


async def require_api_key(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> APIKey:
    """FastAPI dependency: 401 if missing, 403 if invalid/expired/disabled."""
    settings = get_settings()
    raw = extract_key_from_request(request)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_api_key",
                "detail": f"Provide a key via ?{QUERY_PARAM}=..., {HEADER_NAME} header, or Authorization: Bearer.",
            },
        )

    api_key = await lookup_key(raw, session)
    if api_key is None or not raw.startswith(settings.api_key_prefix):
        # The lookup always runs, so a malformed key costs the same time as an
        # unknown one. Both answers are identical, the format of a key is not
        # leaked through the answer or through the answer time.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_api_key", "detail": "API key not recognised."},
        )

    if not api_key.is_usable():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "key_disabled", "detail": "API key is disabled or expired."},
        )

    return api_key


def touch(api_key: APIKey) -> None:
    """Update last_used_at to now. Caller is responsible for committing."""
    api_key.last_used_at = datetime.now(timezone.utc)
