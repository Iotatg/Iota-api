"""Pluggable media provider interface.

A MediaProvider resolves a media_id into metadata AND a stream source. The
caller (the service layer) is responsible for caching the metadata and for
streaming the bytes; the provider only knows how to find them.

Implementations:

- DemoProvider: returns a metadata record pointing at a local licensed
  sample file. Safe to ship in production as a reference; never reaches
  out to the public internet.

To add a real provider:

1. Subclass MediaProvider.
2. Implement search, get_info, get_stream.
3. Register it in app/main.py: provider = YourProvider()  and use
   `app.dependency_overrides[get_provider] = lambda: provider` in tests
   or wire it up in lifespan.

IMPORTANT: This interface is intentionally narrow. Do not add any method
that takes a user-supplied URL and fetches it. The provider pulls from
fixed, allowlisted sources only.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional


@dataclass
class MediaMetadata:
    """Provider-independent metadata record."""

    media_id: str
    title: str
    artist: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: str = "audio/mpeg"
    # Where the actual bytes live (relative to the storage backend)
    storage_key: str = ""
    provider: str = "unknown"
    # Engagement stats where the source exposes them (YouTube's info dicts
    # and flat search entries carry view_count; some providers lack likes).
    views: Optional[int] = None
    likes: Optional[int] = None


@dataclass
class StreamSource:
    """A reference to the actual media bytes."""

    storage_key: str
    size_bytes: int
    mime_type: str
    # If known, a direct public URL the storage backend can issue
    # signed URLs against. None means "ask the storage backend".
    direct_url: Optional[str] = None
    # DASH support: when is_dash is True, direct_url points at a
    # video-only stream and direct_url_audio at the matching
    # audio-only stream. The two must be remuxed together (ffmpeg)
    # before playback; this is how video quality above the merged
    # single-file threshold (1080p / 4K / 8K) is delivered, since
    # YouTube only serves those resolutions as separate streams.
    direct_url_audio: Optional[str] = None
    is_dash: bool = False


class ProviderError(Exception):
    """Base class for provider-level failures."""


class MediaNotFoundError(ProviderError):
    """The requested media_id does not exist in this provider."""


class ProviderUnavailableError(ProviderError):
    """The provider is up but the call failed (network, auth, etc.)."""


class MediaProvider(abc.ABC):
    """Abstract base for media providers."""

    name: str = "abstract"

    @abc.abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        """Return up to `limit` matches for `query`."""

    @abc.abstractmethod
    async def get_info(self, media_id: str) -> MediaMetadata:
        """Return metadata for a single media_id. Raises MediaNotFoundError."""

    @abc.abstractmethod
    async def get_stream(self, media_id: str) -> StreamSource:
        """Return a stream source for the media_id. Raises MediaNotFoundError."""

    async def get_stream_by_type(
        self,
        media_id: str,
        media_type: str = "audio",
        prefer_dash: bool = False,
        max_height: Optional[int] = None,
    ) -> StreamSource:
        """Return a stream source for a specific media type.

        ``media_type`` is ``"audio"`` (default) or ``"video"``.
        ``prefer_dash`` asks providers that can to return a
        higher-quality split (DASH) representation; providers that
        expose a single representation ignore it. The default
        implementation delegates to :meth:`get_stream`.
        """
        return await self.get_stream(media_id)

    async def stream_chunks(
        self, media_id: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        """Default implementation: just an empty async generator. Subclasses
        may override if they want to stream directly from the source
        instead of going through the storage backend."""
        raise NotImplementedError(
            "stream_chunks is provided by the storage backend, not the provider."
        )
        yield b""  # pragma: no cover  (makes this a generator)
