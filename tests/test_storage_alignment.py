"""Regression tests for the storage <-> demo provider path alignment.

Bug: STORAGE_LOCAL_PATH defaulted to ./storage, but DEMO_AUDIO_DIR defaults
to ./storage/audio. The demo provider returns storage_key="<filename>"
(relative to audio dir), so storage would look in ./storage/<filename>
and find nothing. /stream returned 404 with `Audio bytes are not present
in storage.`
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_storage_local_path_default_matches_demo_audio_dir():
    """The two config defaults must point to the same directory.

    This test catches the case where someone changes one default without
    the other. We instantiate Settings() with only the required fields
    so we get the unmodified defaults.
    """
    from app.config import Settings
    s = Settings(admin_token="x" * 64)  # bypass env, get pure defaults
    assert Path(s.storage_local_path).resolve() == Path(s.demo_audio_dir).resolve(), (
        f"STORAGE_LOCAL_PATH default ({s.storage_local_path}) and DEMO_AUDIO_DIR "
        f"default ({s.demo_audio_dir}) must resolve to the same directory."
    )


@pytest.mark.asyncio
async def test_demo_provider_storage_key_resolves_in_storage():
    """LocalStorage and DemoProvider must agree on the same directory.

    Uses temp_audio_dir directly (no app instance) so the test is fast
    and doesn't depend on the FastAPI app/database being up.
    """
    from app.services.demo_provider import DemoProvider
    from app.services.storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "sample-001.mp3").write_bytes(b"FAKEAUDIO" * 512)
        (tmp_path / "manifest.json").write_text(
            '{"sample-001.mp3": {"title": "x", "duration_seconds": 60}}'
        )

        storage = LocalStorage(base_path=str(tmp_path), public_base_url="http://t")
        provider = DemoProvider(audio_dir=str(tmp_path))

        src = await provider.get_stream("sample-001.mp3")
        assert src.storage_key == "sample-001.mp3"
        assert await storage.exists(src.storage_key), (
            f"LocalStorage at {tmp_path} does not contain {src.storage_key}. "
            "DEMO_AUDIO_DIR and STORAGE_LOCAL_PATH are misaligned."
        )
        assert (await storage.size(src.storage_key)) > 1000


@pytest.mark.asyncio
async def test_stream_full_returns_audio_bytes(client, created_key, app_instance):
    """GET /stream/sample-001.mp3 should return a non-trivial body."""
    api_key = created_key["api_key"]
    r = await client.get(
        "/stream/sample-001.mp3", headers={"X-API-Key": api_key}
    )
    assert r.status_code == 200, r.text
    body = r.read()
    # conftest temp_audio_dir writes 4 KiB of FAKEAUDIO bytes
    assert len(body) > 1000
    assert body.startswith(b"FAKEAUDIO")


@pytest.mark.asyncio
async def test_stream_range_returns_partial(client, created_key, app_instance):
    """GET /stream/sample-001.mp3 with bytes=0-99 should return 206 + 100 bytes."""
    api_key = created_key["api_key"]
    r = await client.get(
        "/stream/sample-001.mp3",
        headers={"X-API-Key": api_key, "Range": "bytes=0-99"},
    )
    assert r.status_code == 206, r.text
    assert r.headers["Content-Range"].startswith("bytes 0-99/")
    assert r.headers["Accept-Ranges"] == "bytes"
    assert len(r.content) == 100


@pytest.mark.asyncio
async def test_stream_head_returns_headers_only(client, created_key, app_instance):
    """HEAD /stream should return 200 with no body and full Content-Length."""
    api_key = created_key["api_key"]
    r = await client.head(
        "/stream/sample-001.mp3", headers={"X-API-Key": api_key}
    )
    assert r.status_code == 200, r.text
    assert r.headers["Accept-Ranges"] == "bytes"
    assert int(r.headers["Content-Length"]) > 1000
    # HEAD must not have a body
    assert r.content == b""


@pytest.mark.asyncio
async def test_stream_unsatisfiable_range_returns_416(client, created_key, app_instance):
    """A range past EOF should return 416."""
    api_key = created_key["api_key"]
    r = await client.get(
        "/stream/sample-001.mp3",
        headers={"X-API-Key": api_key, "Range": "bytes=9999999-"},
    )
    assert r.status_code == 416


@pytest.mark.asyncio
async def test_stream_suffix_range(client, created_key, app_instance):
    """bytes=-100 should return the last 100 bytes."""
    api_key = created_key["api_key"]
    r = await client.get(
        "/stream/sample-001.mp3",
        headers={"X-API-Key": api_key, "Range": "bytes=-100"},
    )
    assert r.status_code == 206
    # Total file is 4608 bytes (FAKEAUDIO * 512 = 9*512), so last 100 are 4508-4607
    assert r.headers["Content-Range"].endswith("/4608")
    assert len(r.content) == 100
