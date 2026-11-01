"""Test download endpoint: attachment disposition, Range, auth, kind."""
import pytest


def _isolate_merge_cache(monkeypatch, tmp_path):
    """Keep merged-video results out of the shared repo cache dir.

    The merge cache is a disk directory keyed by media id + height;
    without isolation one test's merge would be served to the next
    one and the working tree would collect multi-MB artifacts.
    """
    import app.routes.download as dl
    from app.config import get_settings

    settings = get_settings().model_copy(
        update={"video_merge_cache_dir": str(tmp_path / "merge-cache")}
    )
    monkeypatch.setattr(dl, "get_settings", lambda: settings)


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
    client, created_key, app_instance, monkeypatch, tmp_path
):
    """kind=video with a DASH source: the route remuxes the
    two streams into a temp file via ffmpeg, serves it
    Range-capable, then removes the temp file."""
    import os
    import tempfile
    from unittest.mock import AsyncMock

    import app.routes.download as dl
    from app.services.media_provider import StreamSource

    _isolate_merge_cache(monkeypatch, tmp_path)
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
    client, created_key, app_instance, monkeypatch, tmp_path
):
    """A DASH download honours Range requests (the merged
    temp file is served like any other seekable file)."""
    import os
    import tempfile
    from unittest.mock import AsyncMock

    import app.routes.download as dl
    from app.services.media_provider import StreamSource

    _isolate_merge_cache(monkeypatch, tmp_path)
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


class TestEffectiveVideoHeight:
    """The requested height must reach the provider *before* the
    stream is resolved, and an explicit 4K request must survive."""

    @staticmethod
    def _capture(provider, height=2160):
        from unittest.mock import AsyncMock
        from app.services.media_provider import StreamSource

        seen = {}

        async def fake(media_id, kind, prefer_dash=False, max_height=None):
            seen["kind"] = kind
            seen["prefer_dash"] = prefer_dash
            seen["max_height"] = max_height
            return StreamSource(
                storage_key="sample-001.mp3",
                size_bytes=4608,
                mime_type="video/mp4",
            )

        provider.get_stream_by_type = fake
        return seen

    @pytest.mark.asyncio
    async def test_default_height_is_720(self, client, created_key, app_instance):
        provider = app_instance.state.provider
        seen = self._capture(provider)
        await client.get(
            "/download/sample-001.mp3",
            params={"key": created_key["api_key"], "kind": "video"},
        )
        assert seen["max_height"] == 720
        assert seen["prefer_dash"] is True

    @pytest.mark.asyncio
    async def test_explicit_4k_request_is_honoured(
        self, client, created_key, app_instance
    ):
        provider = app_instance.state.provider
        seen = self._capture(provider)
        await client.get(
            "/download/sample-001.mp3",
            params={
                "key": created_key["api_key"],
                "kind": "video",
                "max_height": 2160,
            },
        )
        assert seen["max_height"] == 2160

    @pytest.mark.asyncio
    async def test_request_above_hard_cap_is_clamped(
        self, client, created_key, app_instance
    ):
        provider = app_instance.state.provider
        seen = self._capture(provider)
        await client.get(
            "/download/sample-001.mp3",
            params={
                "key": created_key["api_key"],
                "kind": "video",
                "max_height": 4320,
            },
        )
        assert seen["max_height"] == 2160

    @pytest.mark.asyncio
    async def test_audio_is_not_height_capped(
        self, client, created_key, app_instance
    ):
        provider = app_instance.state.provider
        seen = self._capture(provider)
        await client.get(
            "/download/sample-001.mp3",
            params={"key": created_key["api_key"], "kind": "audio"},
        )
        assert seen["max_height"] is None


class TestHlsVideoDownload:
    """An HLS playlist carries no media bytes: the route must remux it
    into a real MP4 instead of proxying the text manifest."""

    @pytest.mark.asyncio
    async def test_hls_source_is_remuxed_and_served(
        self, client, created_key, app_instance, monkeypatch, tmp_path
    ):
        import os
        import tempfile
        from unittest.mock import AsyncMock

        import app.routes.download as dl
        from app.services.media_provider import StreamSource

        _isolate_merge_cache(monkeypatch, tmp_path)
        provider = app_instance.state.provider
        provider.get_stream_by_type = AsyncMock(return_value=StreamSource(
            storage_key="",
            size_bytes=0,
            mime_type="video/mp4",
            direct_url="https://cdn.up.test/variant2160.m3u8",
            direct_url_audio="https://cdn.up.test/audio.m4a",
            is_hls=True,
        ))

        payload = b"FAKEREMUX" * 256
        created = []

        async def fake_merge(video_url, audio_url):
            assert video_url == "https://cdn.up.test/variant2160.m3u8"
            assert audio_url == "https://cdn.up.test/audio.m4a"
            fd, path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            with open(path, "wb") as fh:
                fh.write(payload)
            created.append(path)
            return path

        monkeypatch.setattr(dl, "_merge_hls_to_temp", fake_merge)

        r = await client.get(
            "/download/yt:abc123",
            params={"key": created_key["api_key"], "kind": "video"},
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("video/mp4")
        assert r.headers["accept-ranges"] == "bytes"
        assert r.content == payload
        assert created and not os.path.exists(created[0])

    @pytest.mark.asyncio
    async def test_manifest_direct_url_is_not_proxied(
        self, client, created_key, app_instance, monkeypatch, tmp_path
    ):
        """A playlist URL that arrives without the is_hls flag must
        still be remuxed, never proxied as the media file."""
        import os
        import tempfile
        from unittest.mock import AsyncMock

        import app.routes.download as dl
        from app.services.media_provider import StreamSource

        _isolate_merge_cache(monkeypatch, tmp_path)
        provider = app_instance.state.provider
        provider.get_stream_by_type = AsyncMock(return_value=StreamSource(
            storage_key="",
            size_bytes=0,
            mime_type="video/mp4",
            direct_url="https://cdn.up.test/merged.m3u8",
        ))

        payload = b"FAKEREMUX" * 256

        async def fake_merge(video_url, audio_url):
            assert audio_url is None
            fd, path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            with open(path, "wb") as fh:
                fh.write(payload)
            return path

        monkeypatch.setattr(dl, "_merge_hls_to_temp", fake_merge)

        r = await client.get(
            "/download/yt:abc123",
            params={"key": created_key["api_key"], "kind": "video"},
        )
        assert r.status_code == 200
        assert r.content == payload

    @pytest.mark.asyncio
    async def test_hls_head_reports_no_size(
        self, client, created_key, app_instance, monkeypatch, tmp_path
    ):
        """A HEAD must not trigger the remux, and the merged length is
        unknown until it runs."""
        from unittest.mock import AsyncMock

        import app.routes.download as dl
        from app.services.media_provider import StreamSource

        _isolate_merge_cache(monkeypatch, tmp_path)
        provider = app_instance.state.provider
        provider.get_stream_by_type = AsyncMock(return_value=StreamSource(
            storage_key="",
            size_bytes=0,
            mime_type="video/mp4",
            direct_url="https://cdn.up.test/variant2160.m3u8",
            is_hls=True,
        ))

        called = []

        async def fake_merge(video_url, audio_url):
            called.append(video_url)
            raise AssertionError("HEAD must not remux")

        monkeypatch.setattr(dl, "_merge_hls_to_temp", fake_merge)

        r = await client.head(
            "/download/yt:abc123",
            params={"key": created_key["api_key"], "kind": "video"},
        )
        assert r.status_code == 200
        assert "content-length" not in r.headers
        assert r.headers["accept-ranges"] == "none"
        assert not called


def test_url_is_manifest_detects_playlists():
    from app.routes.download import _url_is_manifest
    assert _url_is_manifest("https://x/v.m3u8?sig=1") is True
    assert _url_is_manifest("https://x/v.mpd") is True
    assert _url_is_manifest("https://x/video.mp4") is False
    assert _url_is_manifest(None) is False
