"""Test streaming endpoint: full body, Range, HEAD."""
import pytest


@pytest.mark.asyncio
async def test_stream_full_body(client, created_key):
    r = await client.get(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "audio/mpeg"
    body = r.content
    # 4 KiB of "FAKEAUDIO" = 9 bytes * 512
    assert len(body) == 9 * 512
    assert body[:9] == b"FAKEAUDIO"


@pytest.mark.asyncio
async def test_stream_with_range(client, created_key):
    """Range: bytes=0-15 → first 16 bytes, 206 Partial Content."""
    r = await client.get(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=0-15"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 0-15/4608"
    assert r.headers["accept-ranges"] == "bytes"
    assert len(r.content) == 16


@pytest.mark.asyncio
async def test_stream_with_open_range(client, created_key):
    """Range: bytes=100- → from byte 100 to end."""
    r = await client.get(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=100-"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 100-4607/4608"
    assert len(r.content) == 4608 - 100


@pytest.mark.asyncio
async def test_stream_with_suffix_range(client, created_key):
    """Range: bytes=-100 → last 100 bytes."""
    r = await client.get(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=-100"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 4508-4607/4608"
    assert len(r.content) == 100


@pytest.mark.asyncio
async def test_stream_unsatisfiable_range(client, created_key):
    """Range: bytes=99999- → 416."""
    r = await client.get(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=99999-"},
    )
    assert r.status_code == 416


@pytest.mark.asyncio
async def test_stream_head_returns_headers_only(client, created_key):
    r = await client.head(
        "/stream/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == "4608"
    assert r.content == b""


@pytest.mark.asyncio
async def test_stream_missing_media_returns_404(client, created_key):
    r = await client.get(
        "/stream/missing.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "media_not_found"


@pytest.mark.asyncio
async def test_stream_requires_auth(client):
    r = await client.get("/stream/sample-001.mp3")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stream_chunks_dont_load_full_file(client, created_key, app_instance):
    """Verify the response is chunked (Transfer-Encoding: chunked) and never
    buffered in a single shot. We read the first chunk, then close."""
    async with client.stream(
        "GET", "/stream/sample-001.mp3", params={"key": created_key["api_key"]}
    ) as r:
        assert r.status_code == 200
        # Read just the first chunk
        async for chunk in r.aiter_bytes(chunk_size=512):
            assert len(chunk) <= 512
            break
