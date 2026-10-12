"""Persistent stream-URL cache backed by the app database.

Stores resolved upstream URLs (and their metadata) so the URL cache
survives a process restart and is shared across lookups. Only URL
pointers are cached — media bytes are always streamed on-demand from
the upstream CDN. All operations are best-effort: a cache failure
must never break streaming.
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

from sqlalchemy import delete, select

from app import database
from app.models.stream_cache import StreamCache
from app.services.media_provider import MediaMetadata
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StreamCacheService:
    """Database-backed persistent cache for resolved stream URLs."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl

    async def get(
        self, media_id: str
    ) -> Optional[Tuple[str, MediaMetadata]]:
        """Return a still-valid (url, metadata) pair, or None."""
        try:
            now = time.time()
            async with database.AsyncSessionLocal() as session:
                row = (
                    await session.execute(
                        select(StreamCache).where(
                            StreamCache.media_id == media_id
                        )
                    )
                ).scalar_one_or_none()
        except Exception as e:
            logger.warning("stream_cache_get_error", extra={"err": str(e)})
            return None
        if row is None or row.expires_at <= now:
            return None
        meta = MediaMetadata(
            media_id=media_id,
            title=row.title or media_id,
            artist=row.artist,
            duration_seconds=row.duration,
            mime_type=row.mime_type or "audio/mpeg",
            provider="yt",
        )
        return row.url, meta

    async def put(
        self,
        media_id: str,
        url: str,
        meta: MediaMetadata,
        ttl: Optional[float] = None,
    ) -> None:
        """Upsert a resolved URL with its expiry."""
        try:
            expires = time.time() + (self._ttl if ttl is None else ttl)
            async with database.AsyncSessionLocal() as session:
                await session.merge(
                    StreamCache(
                        media_id=media_id,
                        url=url,
                        mime_type=meta.mime_type,
                        title=meta.title,
                        artist=meta.artist,
                        duration=meta.duration_seconds,
                        expires_at=expires,
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning("stream_cache_put_error", extra={"err": str(e)})

    async def invalidate(self, media_id: str) -> None:
        """Drop a cached URL (e.g. it went stale before its TTL)."""
        try:
            async with database.AsyncSessionLocal() as session:
                await session.execute(
                    delete(StreamCache).where(
                        StreamCache.media_id == media_id
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning("stream_cache_invalidate_error", extra={"err": str(e)})

    async def purge_expired(self) -> int:
        """Delete expired entries. Returns the number removed."""
        try:
            now = time.time()
            async with database.AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(StreamCache).where(StreamCache.expires_at <= now)
                )
                await session.commit()
                return result.rowcount or 0
        except Exception as e:
            logger.warning("stream_cache_purge_error", extra={"err": str(e)})
            return 0
