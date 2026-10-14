"""Range pass-through proxy for remote stream sources.

When a provider returns a ``StreamSource`` with ``direct_url`` set, the bytes
live on an upstream server (typically a CDN). The stream route should still
issue a single HTTP Range request to the client, and forward that Range to
the upstream — we never reimplement the streaming protocol, we just relay
the bytes.

This module is intentionally narrow:

- :meth:`StreamProxy.head` returns ``(size_bytes, accept_ranges)`` so the
  route can parse Range headers and return correct 200/206/416 responses.
- :meth:`StreamProxy.stream` is an async iterator that yields chunks from
  the upstream, honouring a ``Range: bytes=start-end`` header.

Upstream errors are translated into ``ProviderUnavailableError`` so the
route returns a structured 502/503.
"""
from __future__ import annotations

import asyncio
import http.cookiejar
import os
import re
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Tuple

import httpx

from app.services.media_provider import ProviderUnavailableError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default request timeout for upstream HEAD/GET. Connect is bounded
# separately so a slow CDN does not stall the client indefinitely.
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 60.0

# How many chunks each parallel segment may buffer ahead of the
# consumer. Keeps memory bounded regardless of file size.
_PARALLEL_QUEUE_DEPTH = 8
# Default number of concurrent Range connections. CDNs such as
# YouTube's googlevideo throttle a single TCP stream to a few
# dozen KB/s but allow several MB/s in aggregate, so a handful of
# connections lifts throughput dramatically (the same technique
# yt-dlp uses for its chunked downloader).
_PARALLEL_WORKERS = 4
# Attempts per parallel segment before the fetch fails. Google Video
# CDN connections can stall or reset mid-transfer on large (4K)
# segments; resuming from the bytes already received recovers cheaply.
_SEGMENT_ATTEMPTS = 4


@dataclass
class UpstreamHead:
    size_bytes: int
    accept_ranges: bool
    content_type: str = "application/octet-stream"
    supports_range: bool = True


def _load_cookie_jar(cookies_file: Optional[str]) -> Optional[http.cookiejar.CookieJar]:
    """Load a Netscape cookie file for upstream media requests.

    googlevideo URLs minted from a signed-in session can be rejected
    with HTTP 403 when the fetch carries no session cookies, so the
    same cookie file yt-dlp uses for extraction is attached here.
    Expired cookies are ignored on load: YouTube rotates them often
    and a half-stale jar still passes the CDN check.
    """
    if not cookies_file or not os.path.isfile(cookies_file):
        return None
    jar = http.cookiejar.MozillaCookieJar(cookies_file)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except (OSError, http.cookiejar.LoadError) as exc:
        logger.warning("upstream_cookies_load_failed", extra={"err": str(exc)})
        return None
    if not jar:
        return None
    return jar


class StreamProxy:
    """Range-aware HTTP proxy for remote media bytes."""

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        cookies_file: Optional[str] = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._cookies_file = cookies_file
        self._cookie_jar: Optional[http.cookiejar.CookieJar] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=10.0, pool=10.0
            )
            if self._cookies_file and self._cookie_jar is None:
                self._cookie_jar = _load_cookie_jar(self._cookies_file)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                cookies=self._cookie_jar,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def head(self, url: str) -> UpstreamHead:
        """Probe the upstream for size and Range support.

        Issues a HEAD request, falling back to a ranged GET (0-0) when the
        upstream rejects HEAD (some CDNs return 405 for HEAD but still
        return useful headers on GET). Google video CDNS intermittently
        reset these probes, so the whole probe is retried a few times.
        """
        last_exc: Optional[BaseException] = None
        for attempt in range(1, _SEGMENT_ATTEMPTS + 1):
            try:
                return await self._probe(url)
            except (httpx.HTTPError, ProviderUnavailableError) as exc:
                last_exc = exc
                if attempt < _SEGMENT_ATTEMPTS:
                    await asyncio.sleep(0.4 * attempt)
        raise ProviderUnavailableError(
            f"upstream HEAD failed after retries: {last_exc}"
        ) from last_exc

    async def _probe(self, url: str) -> UpstreamHead:
        client = await self._get_client()
        try:
            resp = await client.head(url)
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(f"upstream HEAD failed: {e}") from e
        if resp.status_code in (405, 403) or resp.headers.get("content-length") is None:
            try:
                resp = await client.get(url, headers={"Range": "bytes=0-0"})
            except httpx.HTTPError as e:
                raise ProviderUnavailableError(f"upstream GET failed: {e}") from e
        if resp.status_code not in (200, 206):
            raise ProviderUnavailableError(
                f"upstream returned HTTP {resp.status_code} on HEAD"
            )
        size_raw = resp.headers.get("content-length")
        try:
            size = int(size_raw) if size_raw is not None else 0
        except (TypeError, ValueError):
            size = 0
        if resp.status_code == 206 and size_raw == "1":
            # A 0-0 probe reports its own length, not the object's total.
            size = self._total_from_content_range(resp.headers.get("content-range"))
        elif size == 0:
            # Chunked/streamed responses omit content-length entirely.
            size = self._total_from_content_range(resp.headers.get("content-range"))
            if size == 0:
                try:
                    probe = await client.get(url, headers={"Range": "bytes=0-1023"})
                except httpx.HTTPError as e:
                    raise ProviderUnavailableError(f"upstream GET failed: {e}") from e
                if probe.status_code == 206:
                    size = self._total_from_content_range(
                        probe.headers.get("content-range")
                    )
                await probe.aclose()
        accept_ranges = (resp.headers.get("accept-ranges", "").lower() == "bytes")
        content_type = resp.headers.get("content-type", "application/octet-stream")
        return UpstreamHead(
            size_bytes=size,
            accept_ranges=accept_ranges,
            content_type=content_type.split(";")[0].strip() or "application/octet-stream",
            supports_range=accept_ranges or resp.status_code == 206,
        )

    @staticmethod
    def _total_from_content_range(header: Optional[str]) -> int:
        m = re.search(r"/(\d+)\s*$", header or "")
        return int(m.group(1)) if m else 0

    async def stream(
        self,
        url: str,
        start: int,
        end: int,
        chunk_size: int = 65536,
    ) -> AsyncIterator[bytes]:
        """Yield bytes [start, end] from the upstream, honouring Range.

        The client should already have validated start/end against the
        upstream Content-Length; this method trusts those bounds.
        """
        if start < 0:
            raise ValueError("start must be >= 0")
        if end < start:
            raise ValueError("end must be >= start")
        headers = {"Range": f"bytes={start}-{end}"}
        client = await self._get_client()
        try:
            resp = await client.send(
                client.build_request("GET", url, headers=headers), stream=True
            )
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(f"upstream GET failed: {e}") from e
        if resp.status_code not in (200, 206):
            await resp.aclose()
            raise ProviderUnavailableError(
                f"upstream returned HTTP {resp.status_code} on stream"
            )
        try:
            async for chunk in resp.aiter_bytes(chunk_size):
                if chunk:
                    yield chunk
        finally:
            await resp.aclose()

    async def stream_parallel(
        self,
        url: str,
        start: int,
        end: int,
        chunk_size: int = 65536,
        workers: int = _PARALLEL_WORKERS,
    ) -> AsyncIterator[bytes]:
        """Yield bytes [start, end] over concurrent Range requests.

        A single connection to a CDN is often throttled to a few
        dozen KB/s. Splitting the byte range across a few
        concurrent connections (the same technique yt-dlp uses)
        lifts aggregate throughput to several MB/s. Bytes are
        emitted strictly in order; each segment buffers only a
        small number of chunks, so memory stays bounded.
        """
        if start < 0:
            raise ValueError("start must be >= 0")
        if end < start:
            raise ValueError("end must be >= start")
        total = end - start + 1
        workers = max(1, min(workers, 16))
        # Too small to benefit from parallelism.
        if total < chunk_size * workers:
            async for chunk in self.stream(url, start, end, chunk_size):
                yield chunk
            return

        seg_len = (total + workers - 1) // workers
        segments: list[Tuple[int, int]] = []
        for i in range(workers):
            s = start + i * seg_len
            e = min(start + (i + 1) * seg_len - 1, end)
            if s > e:
                break
            segments.append((s, e))

        client = await self._get_client()
        queues: list[asyncio.Queue] = [
            asyncio.Queue(maxsize=_PARALLEL_QUEUE_DEPTH) for _ in segments
        ]
        errors: list[Optional[BaseException]] = [None] * len(segments)

        async def _produce(idx: int, s: int, e: int) -> None:
            seg_total = e - s + 1
            got = 0
            last_exc: Optional[BaseException] = None
            try:
                for attempt in range(1, _SEGMENT_ATTEMPTS + 1):
                    cur = s + got
                    if cur > e:
                        break
                    try:
                        resp = await client.send(
                            client.build_request(
                                "GET", url, headers={"Range": f"bytes={cur}-{e}"}
                            ),
                            stream=True,
                        )
                        try:
                            if resp.status_code not in (200, 206):
                                raise ProviderUnavailableError(
                                    f"upstream returned HTTP {resp.status_code} on stream"
                                )
                            async for chunk in resp.aiter_bytes(chunk_size):
                                if chunk:
                                    await queues[idx].put(chunk)
                                    got += len(chunk)
                        finally:
                            await resp.aclose()
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        last_exc = exc
                    if got >= seg_total:
                        last_exc = None
                        break
                    if last_exc is None:
                        last_exc = ProviderUnavailableError(
                            f"segment truncated at {got}/{seg_total} bytes"
                        )
                    if attempt < _SEGMENT_ATTEMPTS:
                        await asyncio.sleep(0.5 * attempt)
                if got < seg_total and last_exc is not None:
                    errors[idx] = last_exc
            finally:
                await queues[idx].put(None)

        tasks = [
            asyncio.create_task(_produce(i, s, e))
            for i, (s, e) in enumerate(segments)
        ]
        try:
            for i, q in enumerate(queues):
                while True:
                    chunk = await q.get()
                    if chunk is None:
                        break
                    yield chunk
                if errors[i] is not None:
                    raise errors[i]
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
