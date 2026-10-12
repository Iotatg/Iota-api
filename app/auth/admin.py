"""Admin authentication via the ADMIN_TOKEN environment variable.

Comparison is constant-time to prevent timing attacks.
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """FastAPI dependency: 401 if X-Admin-Token is missing or wrong."""
    settings = get_settings()
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_admin_token", "detail": "X-Admin-Token header required."},
        )
    if not hmac.compare_digest(x_admin_token.encode("utf-8"), settings.admin_token.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "invalid_admin_token", "detail": "Admin token does not match."},
        )
