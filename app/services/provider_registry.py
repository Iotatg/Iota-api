"""Provider registry: maps prefixed media_ids to MediaProvider instances.

media_id format: ``<prefix>:<id>`` where prefix is one of the provider names
registered at startup (e.g. ``yt``, ``sp``, ``jv``, ``sc``, ``dz``, ``am``,
``mb``, ``bp``, ``rs``, ``demo``). A bare id (no colon) is treated as
``demo:<id>`` for backward compatibility with the existing DEMO-only deployment.

A provider is included in the registry only if its ``enabled`` property is
True — providers self-disable when their credentials are missing. This keeps
the DemoProvider-only path identical to today when no keys are set.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Iterable, List, Optional, Tuple

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEMO_PREFIX = "demo"
DEMO_BARE_ALIAS = "demo"  # bare ids route here


class ProviderRegistry(MediaProvider):
    """A MediaProvider that dispatches to a child provider by prefix.

    The registry itself satisfies the MediaProvider contract (search,
    get_info, get_stream) so it can be dropped into the existing
    ``get_provider`` dependency without changing the routes.
    """

    name = "registry"

    def __init__(self, providers: Iterable[MediaProvider]) -> None:
        # Map: prefix -> provider. Disabled providers are dropped entirely.
        self._by_prefix: Dict[str, MediaProvider] = {}
        for p in providers:
            if not getattr(p, "enabled", True):
                logger.info("provider_disabled", extra={"provider": p.name})
                continue
            self._by_prefix[p.name] = p
            logger.info("provider_enabled", extra={"provider": p.name})
        if not self._by_prefix:
            raise RuntimeError("ProviderRegistry: no enabled providers configured")

    @property
    def enabled(self) -> bool:
        return bool(self._by_prefix)

    @property
    def providers(self) -> Dict[str, MediaProvider]:
        return dict(self._by_prefix)

    def split(self, media_id: str) -> Tuple[str, str]:
        """Parse ``<prefix>:<id>`` into (prefix, id). Bare id -> (demo, id)."""
        if not media_id:
            raise MediaNotFoundError("empty media_id")
        if ":" in media_id:
            prefix, _, rest = media_id.partition(":")
            prefix = prefix.strip().lower()
            rest = rest.strip()
            if not prefix or not rest:
                raise MediaNotFoundError(f"invalid media_id: {media_id!r}")
            return prefix, rest
        return DEMO_BARE_ALIAS, media_id

    def resolve(self, media_id: str) -> Tuple[MediaProvider, str]:
        prefix, native_id = self.split(media_id)
        provider = self._by_prefix.get(prefix)
        if provider is None:
            raise MediaNotFoundError(f"unknown provider prefix: {prefix!r}")
        return provider, native_id

    async def get_info(self, media_id: str) -> MediaMetadata:
        provider, native_id = self.resolve(media_id)
        meta = await provider.get_info(native_id)
        # Preserve the original prefixed id so the caller can echo it back.
        if ":" not in media_id and provider.name == DEMO_BARE_ALIAS:
            return meta
        return MediaMetadata(
            media_id=media_id,
            title=meta.title,
            artist=meta.artist,
            duration_seconds=meta.duration_seconds,
            thumbnail_url=meta.thumbnail_url,
            size_bytes=meta.size_bytes,
            mime_type=meta.mime_type,
            storage_key=meta.storage_key,
            provider=meta.provider,
            views=meta.views,
            likes=meta.likes,
        )

    async def get_stream(self, media_id: str) -> StreamSource:
        provider, native_id = self.resolve(media_id)
        return await provider.get_stream(native_id)

    async def get_stream_by_type(
        self,
        media_id: str,
        media_type: str = "audio",
        prefer_dash: bool = False,
        max_height: Optional[int] = None,
    ) -> StreamSource:
        provider, native_id = self.resolve(media_id)
        return await provider.get_stream_by_type(
            native_id, media_type, prefer_dash, max_height
        )

    async def invalidate_stream(self, media_id: str) -> None:
        """Drop a cached stream URL in the child provider.

        Upstream URLs can be revoked before their TTL, and the routes
        drop them on failure so the next request re-resolves. Without
        this delegation the routes' getattr found no method on the
        registry, so a poisoned URL stayed cached for its full TTL
        and every request kept replaying it. Accepts the prefixed id
        (the child providers strip their own prefix).
        """
        provider, _native_id = self.resolve(media_id)
        invalidate = getattr(provider, "invalidate_stream", None)
        if callable(invalidate):
            await invalidate(media_id)

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        """Fan out to every enabled provider, dedup by canonical media_id."""
        if not query or not query.strip():
            return []
        per_provider = max(1, limit // max(1, len(self._by_prefix)))
        tasks = [
            self._safe_search(p, query, per_provider)
            for p in self._by_prefix.values()
        ]
        results_lists = await asyncio.gather(*tasks)
        seen: set = set()
        merged: List[MediaMetadata] = []
        for results in results_lists:
            for meta in results:
                # Prefix the id with the provider name so /info and /stream
                # can route back to the same provider.
                full_id = f"{meta.provider}:{meta.media_id}"
                if full_id in seen or meta.media_id in seen:
                    continue
                seen.add(full_id)
                seen.add(meta.media_id)
                merged.append(MediaMetadata(
                    media_id=full_id,
                    title=meta.title,
                    artist=meta.artist,
                    duration_seconds=meta.duration_seconds,
                    thumbnail_url=meta.thumbnail_url,
                    size_bytes=meta.size_bytes,
                    mime_type=meta.mime_type,
                    storage_key=meta.storage_key,
                    provider=meta.provider,
                    views=meta.views,
                    likes=meta.likes,
                ))
                if len(merged) >= limit:
                    return merged
        return merged

    @staticmethod
    async def _safe_search(
        provider: MediaProvider, query: str, limit: int
    ) -> List[MediaMetadata]:
        try:
            return await provider.search(query, limit=limit)
        except Exception as e:
            logger.warning("provider_search_failed", extra={
                "provider": provider.name, "err": str(e),
            })
            return []


def find_youtube_provider(provider: MediaProvider) -> Optional[MediaProvider]:
    """The YouTube provider inside a registry (or the provider itself
    when a bare YouTubeProvider is given, e.g. in tests)."""
    providers = getattr(provider, "providers", None)
    if providers is not None:
        return providers.get("yt")
    return provider if getattr(provider, "name", "") == "yt" else None
