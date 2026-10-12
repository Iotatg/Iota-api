"""Test download endpoint: attachment disposition, Range, auth, kind."""
import pytest


@pytest.mark.asyncio
async def test_download_full_body(client, created_key):
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "audio/mpeg"
    assert "attachment" in r.headers["content-disposition"]
    assert "Sample_One.mp3" in r.headers["content-disposition"]
    body = r.content
    # 4 KiB of "FAKEAUDIO" = 9 bytes * 512
    assert len(body) == 9 * 512
    assert body[:9] == b"FAKEAUDIO"


@pytest.mark.asyncio
async def test_download_video_kind(client, created_key):
    """Demo provider exposes a single representation; kind=video
    still resolves (ABC default delegates to get_stream)."""
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"], "kind": "video"},
    )
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_download_invalid_kind(client, created_key):
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"], "kind": "bogus"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_kind"


@pytest.mark.asyncio
async def test_download_with_range(client, created_key):
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=0-15"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 0-15/4608"
    assert r.headers["accept-ranges"] == "bytes"
    assert "attachment" in r.headers["content-disposition"]
    assert len(r.content) == 16


@pytest.mark.asyncio
async def test_download_head_returns_headers_only(client, created_key):
    r = await client.head(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == "4608"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content == b""


@pytest.mark.asyncio
async def test_download_missing_media_returns_404(client, created_key):
    r = await client.get(
        "/download/missing.mp3",
        params={"key": created_key["api_key"]},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "media_not_found"


@pytest.mark.asyncio
async def test_download_requires_auth(client):
    r = await client.get("/download/sample-001.mp3")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_download_unsatisfiable_range(client, created_key):
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"]},
        headers={"Range": "bytes=99999-"},
    )
    assert r.status_code == 416


@pytest.mark.asyncio
async def test_download_dash_video_merges_and_streams(
    client, created_key, app_instance, monkeypatch
):
    """kind=video with a DASH source: the route remuxes the
    two streams into a temp file via ffmpeg, serves it
    Range-capable, then removes the temp file."""
    import os
    import tempfile
    from unittest.mock import AsyncMock

    import app.routes.download as dl
    from app.services.media_provider import StreamSource

    provider = app_instance.state.provider
    dash_src = StreamSource(
        storage_key="",
        size_bytes=0,
        mime_type="video/mp4",
        direct_url="https://cdn.up.test/video-only.mp4",
        direct_url_audio="https://cdn.up.test/audio-only.m4a",
        is_dash=True,
    )
    provider.get_stream_by_type = AsyncMock(return_value=dash_src)

    payload = b"FAKEVIDEO" * 256  # 2 KiB
    created = []

    async def fake_merge(stream_proxy, video_url, audio_url, workers):
        assert video_url == dash_src.direct_url
        assert audio_url == dash_src.direct_url_audio
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        with open(path, "wb") as fh:
            fh.write(payload)
        created.append(path)
        return path

    monkeypatch.setattr(dl, "_merge_dash_to_temp", fake_merge)

    r = await client.get(
        "/download/yt:abc123",
        params={"key": created_key["api_key"], "kind": "video"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("video/mp4")
    assert "attachment" in r.headers["content-disposition"]
    assert r.content == payload
    # the merged temp file is removed once streaming finishes
    assert created and not os.path.exists(created[0])


@pytest.mark.asyncio
async def test_download_dash_video_with_range(
    client, created_key, app_instance, monkeypatch
):
    """A DASH download honours Range requests (the merged
    temp file is served like any other seekable file)."""
    import os
    import tempfile
    from unittest.mock import AsyncMock

    import app.routes.download as dl
    from app.services.media_provider import StreamSource

    provider = app_instance.state.provider
    dash_src = StreamSource(
        storage_key="",
        size_bytes=0,
        mime_type="video/mp4",
        direct_url="https://cdn.up.test/video-only.mp4",
        direct_url_audio="https://cdn.up.test/audio-only.m4a",
        is_dash=True,
    )
    provider.get_stream_by_type = AsyncMock(return_value=dash_src)

    payload = b"FAKEVIDEO" * 256  # 2 KiB

    async def fake_merge(stream_proxy, video_url, audio_url, workers):
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        with open(path, "wb") as fh:
            fh.write(payload)
        return path

    monkeypatch.setattr(dl, "_merge_dash_to_temp", fake_merge)

    r = await client.get(
        "/download/yt:abc123",
        params={"key": created_key["api_key"], "kind": "video"},
        headers={"Range": "bytes=0-15"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-15/{len(payload)}"
    assert r.headers["content-type"].startswith("video/mp4")
    assert r.content == payload[:16]


@pytest.mark.asyncio
async def test_fetch_url_to_temp_writes_parallel_bytes():
    """_fetch_url_to_temp downloads a URL through the
    parallel Range proxy and writes the bytes to a temp
    file that the caller owns."""
    import os
    from unittest.mock import AsyncMock, MagicMock

    import app.routes.download as dl
    from app.services.stream_proxy import UpstreamHead

    payload = b"PARALLEL" * 512  # 4 KiB

    proxy = MagicMock()
    proxy.head = AsyncMock(return_value=UpstreamHead(
        size_bytes=len(payload),
        accept_ranges=True,
        content_type="video/mp4",
        supports_range=True,
    ))

    async def fake_parallel(url, start, end, chunk_size=65536, workers=4):
        for i in range(0, len(payload), chunk_size):
            yield payload[i:i + chunk_size]

    proxy.stream_parallel = fake_parallel
    proxy.stream = AsyncMock()

    path = await dl._fetch_url_to_temp(
        proxy, "https://cdn.up.test/v.mp4", 4
    )
    try:
        with open(path, "rb") as fh:
            assert fh.read() == payload
    finally:
        os.unlink(path)
    # a range-capable upstream must be fetched in parallel
    proxy.stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_mp3_transcodes_and_streams(
    client, created_key, app_instance, monkeypatch
):
    """format=mp3 transcodes the upstream audio to MP3 on
    the fly (embedding ID3 title/artist tags) and streams
    it; no bytes are written to disk."""
    from unittest.mock import AsyncMock

    import app.routes.download as dl
    from app.services.media_provider import MediaMetadata, StreamSource

    provider = app_instance.state.provider
    m4a_src = StreamSource(
        storage_key="",
        size_bytes=0,
        mime_type="audio/mp4",
        direct_url="https://cdn.up.test/audio.m4a",
    )
    provider.get_stream_by_type = AsyncMock(return_value=m4a_src)
    provider.get_info = AsyncMock(return_value=MediaMetadata(
        media_id="abc123", title="Song Title", artist="Artist Name",
    ))

    mp3_payload = b"ID3" + b"FAKEMP3DATA" * 64

    class _Reader:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        async def read(self, n=-1):
            return self._chunks.pop(0) if self._chunks else b""

    class _Proc:
        def __init__(self):
            self.returncode = None
            self.stdout = _Reader([mp3_payload])
            self.stderr = _Reader([])

        async def wait(self):
            self.returncode = 0
            return 0

        def kill(self):
            self.returncode = -9

    proc = _Proc()
    captured = {}

    async def fake_exec(*args, **kwargs):
        captured["cmd"] = list(args)
        return proc

    monkeypatch.setattr(dl.asyncio, "create_subprocess_exec", fake_exec)

    r = await client.get(
        "/download/yt:abc123",
        params={
            "key": created_key["api_key"],
            "kind": "audio",
            "format": "mp3",
        },
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert "attachment" in r.headers["content-disposition"]
    assert ".mp3" in r.headers["content-disposition"]
    assert r.content == mp3_payload
    # the ffmpeg command must use libmp3lame and embed the tags
    cmd = captured["cmd"]
    assert "libmp3lame" in cmd
    assert any(a == "title=Song Title" for a in cmd)
    assert any(a == "artist=Artist Name" for a in cmd)


@pytest.mark.asyncio
async def test_download_mp3_head_reports_content_type(
    client, created_key, app_instance
):
    """HEAD with format=mp3 reports audio/mpeg and the .mp3
    filename without a content-length (the size is only
    known after a full transcode)."""
    from unittest.mock import AsyncMock

    import app.routes.download as dl  # noqa: F401  (ensures module import)
    from app.services.media_provider import MediaMetadata, StreamSource

    provider = app_instance.state.provider
    m4a_src = StreamSource(
        storage_key="",
        size_bytes=0,
        mime_type="audio/mp4",
        direct_url="https://cdn.up.test/audio.m4a",
    )
    provider.get_stream_by_type = AsyncMock(return_value=m4a_src)
    provider.get_info = AsyncMock(return_value=MediaMetadata(
        media_id="abc123", title="Song Title", artist="Artist Name",
    ))

    r = await client.head(
        "/download/yt:abc123",
        params={
            "key": created_key["api_key"],
            "kind": "audio",
            "format": "mp3",
        },
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert ".mp3" in r.headers["content-disposition"]


def test_content_disposition_non_ascii_is_header_safe():
    from app.routes.download import _content_disposition
    header = _content_disposition("कन्हान_भजन.mp3")
    header.encode("latin-1")
    assert "filename*=UTF-8''" in header
    assert "attachment" in header


def test_content_disposition_strips_quotes_and_semicolons():
    from app.routes.download import _content_disposition
    header = _content_disposition('a";b"c.txt')
    header.encode("latin-1")
    safe_part = header.split('filename="')[1].split('";')[0]
    assert '"' not in safe_part and ";" not in safe_part


@pytest.mark.asyncio
async def test_download_max_height_param_accepted(client, created_key):
    """Providers that ignore DASH caps must still serve the request."""
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"], "kind": "video", "max_height": 1080},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_download_max_height_bounds_validated(client, created_key):
    r = await client.get(
        "/download/sample-001.mp3",
        params={"key": created_key["api_key"], "kind": "video", "max_height": 99999},
    )
    assert r.status_code == 422
