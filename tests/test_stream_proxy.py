"""Tests for StreamProxy — Range pass-through to a remote upstream.

We inject an ``httpx.AsyncClient`` with a ``MockTransport`` so the test
does not touch the real network. The proxy translates HTTP semantics
(200/206/416, Content-Length, Accept-Ranges) but never re-implements
the streaming protocol — it just relays bytes.
"""
from __future__ import annotations

import pytest
import httpx

from app.services.media_provider import ProviderUnavailableError
from app.services.stream_proxy import StreamProxy


def _client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(timeout=10.0, transport=transport, follow_redirects=True)


def _make_response(status: int, headers: dict, body: bytes = b"") -> httpx.Response:
    return httpx.Response(status, headers=headers, content=body)


class TestHead:
    def test_head_returns_size_and_accept_ranges(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "HEAD"
            return _make_response(200, {
                "content-length": "1024",
                "accept-ranges": "bytes",
                "content-type": "audio/mpeg",
            })
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        head = asyncio.get_event_loop().run_until_complete(
            proxy.head("https://up.test/audio.mp3")
        )
        assert head.size_bytes == 1024
        assert head.accept_ranges is True
        assert head.content_type == "audio/mpeg"
        assert head.supports_range is True

    def test_head_falls_back_to_ranged_get_on_405(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "HEAD":
                return _make_response(405, {})
            # GET with Range: bytes=0-0
            assert request.headers.get("range") == "bytes=0-0"
            return _make_response(206, {
                "content-length": "1",
                "content-range": "bytes 0-0/5000",
                "accept-ranges": "bytes",
                "content-type": "audio/mpeg",
            }, body=b"X")
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        head = asyncio.get_event_loop().run_until_complete(
            proxy.head("https://up.test/audio.mp3")
        )
        assert head.size_bytes == 5000  # derived from Content-Range total
        assert head.accept_ranges is True

    def test_head_derives_size_for_chunked_upstream(self):
        # catbox-style: HEAD resets, chunked GETs omit content-length,
        # but a ranged GET reveals the total via Content-Range.
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "HEAD":
                return _make_response(200, {"content-type": "audio/mpeg"})
            assert request.headers.get("range") == "bytes=0-0"
            return httpx.Response(
                206,
                headers={
                    "content-range": "bytes 0-0/307123",
                    "content-type": "audio/mpeg",
                },
                content=b"X",
            )
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        head = asyncio.get_event_loop().run_until_complete(
            proxy.head("https://up.test/audio.mp3")
        )
        assert head.size_bytes == 307123
        assert head.supports_range is True

    def test_head_streams_full_size_probe_when_no_range_support(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "HEAD":
                return _make_response(200, {"content-type": "audio/mpeg"})
            if request.headers.get("range") == "bytes=0-0":
                return _make_response(200, {"content-type": "audio/mpeg"})
            assert request.headers.get("range") == "bytes=0-1023"
            return _make_response(206, {"content-range": "bytes 0-1023/9000"}, b"x" * 1024)
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        head = asyncio.get_event_loop().run_until_complete(
            proxy.head("https://up.test/audio.mp3")
        )
        assert head.size_bytes == 9000

    def test_head_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(500, {})
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        with pytest.raises(ProviderUnavailableError):
            asyncio.get_event_loop().run_until_complete(
                proxy.head("https://up.test/audio.mp3")
            )


class TestStream:
    def test_stream_yields_chunks(self):
        chunks = [b"AAAA", b"BBBB", b"CCCC"]
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers.get("range") == "bytes=0-11"
            return _make_response(206, {
                "content-length": str(sum(len(c) for c in chunks)),
                "content-range": f"bytes 0-11/100",
                "content-type": "audio/mpeg",
            }, body=b"".join(chunks))
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        async def collect():
            out = bytearray()
            async for c in proxy.stream("https://up.test/audio.mp3", 0, 11, 8):
                out += c
            return bytes(out)
        result = asyncio.get_event_loop().run_until_complete(collect())
        assert result == b"AAAABBBBCCCC"

    def test_stream_full_body_when_range_unsupported(self):
        body = b"fullbody"
        def handler(request: httpx.Request) -> httpx.Response:
            # Server ignores Range and returns 200
            return _make_response(200, {
                "content-length": str(len(body)),
                "content-type": "audio/mpeg",
            }, body=body)
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        async def collect():
            out = bytearray()
            async for c in proxy.stream("https://up.test/audio.mp3", 0, 7, 8):
                out += c
            return bytes(out)
        result = asyncio.get_event_loop().run_until_complete(collect())
        assert result == body

    def test_stream_upstream_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _make_response(502, {})
        proxy = StreamProxy(client=_client(handler))
        import asyncio
        async def collect():
            async for _ in proxy.stream("https://up.test/audio.mp3", 0, 10, 8):
                pass
        with pytest.raises(ProviderUnavailableError):
            asyncio.get_event_loop().run_until_complete(collect())

    def test_stream_invalid_bounds(self):
        proxy = StreamProxy(client=_client(lambda r: _make_response(200, {})))
        import asyncio
        async def drive():
            agen = proxy.stream("https://up.test/audio.mp3", 5, 3, 8)
            await agen.__anext__()
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(drive())


class TestStreamParallel:
    def _body(self):
        return b"0123456789ABCDEF"

    def _serve_range(self, body):
        def responder(request: httpx.Request) -> httpx.Response:
            s, e = (int(x) for x in request.headers["range"].split("=")[1].split("-"))
            return _make_response(206, {
                "content-length": str(e - s + 1),
                "content-range": f"bytes {s}-{e}/{len(body)}",
                "content-type": "audio/mpeg",
            }, body=body[s:e + 1])
        return responder

    def test_parallel_resumes_segment_after_stall(self):
        import asyncio
        body = self._body()
        responder = self._serve_range(body)
        stalled = {"done": False}

        def handler(request: httpx.Request) -> httpx.Response:
            s = int(request.headers["range"].split("=")[1].split("-")[0])
            if s == 8 and not stalled["done"]:
                stalled["done"] = True
                raise httpx.ReadError("stalled", request=request)
            return responder(request)

        proxy = StreamProxy(client=_client(handler))

        async def collect():
            out = bytearray()
            async for c in proxy.stream_parallel(
                "https://up.test/v.mp4", 0, len(body) - 1, 4, workers=2
            ):
                out += c
            return bytes(out)

        result = asyncio.get_event_loop().run_until_complete(collect())
        assert result == body
        assert stalled["done"] is True

    def test_parallel_fails_after_retries_exhausted(self):
        import asyncio

        def handler(request: httpx.Request) -> httpx.Response:
            s = int(request.headers["range"].split("=")[1].split("-")[0])
            if s == 8:
                raise httpx.ReadError("broken pipe", request=request)
            return self._serve_range(self._body())(request)

        proxy = StreamProxy(client=_client(handler))

        async def collect():
            async for _ in proxy.stream_parallel(
                "https://up.test/v.mp4", 0, 15, 4, workers=2
            ):
                pass

        with pytest.raises((ProviderUnavailableError, httpx.HTTPError)):
            asyncio.get_event_loop().run_until_complete(collect())
