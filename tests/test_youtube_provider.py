"""Tests for YouTubeProvider.

We monkeypatch ``_run_ytdlp`` (the subprocess call) so no real yt-dlp is
invoked and no network is touched. The tests cover:

- id validation (11-char YouTube id)
- ``get_info`` from Data API v3
- ``get_info`` from yt-dlp fallback
- ``get_stream`` returns a StreamSource with a direct_url
- ``search`` fan-out (Data API + yt-dlp)
- ``enabled`` property responds to credentials
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.media_provider import (
    MediaNotFoundError,
    ProviderUnavailableError,
)
from app.services.youtube_provider import (
    YouTubeProvider,
    _pick_dash_formats,
    _run_ytdlp,
    _YtdlpResult,
)


def _ok_json(data: dict) -> _YtdlpResult:
    return _YtdlpResult(ok=True, data=json.dumps(data).encode("utf-8"))


def _ok_lines(items: list[dict]) -> _YtdlpResult:
    body = "\n".join(json.dumps(i) for i in items).encode("utf-8")
    return _YtdlpResult(ok=True, data=body)


def _ok_text(text: str) -> _YtdlpResult:
    return _YtdlpResult(ok=True, data=text.encode("utf-8"))


def _fail(stderr: str = "boom") -> _YtdlpResult:
    return _YtdlpResult(ok=False, stderr=stderr)


class TestIdValidation:
    def test_valid_id(self):
        assert YouTubeProvider.validate_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    @pytest.mark.parametrize("bad", [
        "", "short", "way-way-way-way-way-way-way-way-way-way",
        "contains spaces!",
        "x" * 12,
    ])
    def test_invalid_id(self, bad):
        with pytest.raises(MediaNotFoundError):
            YouTubeProvider.validate_id(bad)


class TestEnabled:
    def test_enabled_with_api_key(self):
        p = YouTubeProvider(api_key="AIza-test")
        assert p.enabled is True

    def test_disabled_with_no_creds_and_no_yt_dlp(self):
        with patch(
            "app.services.youtube_provider._resolve_ytdlp_argv", return_value=[]
        ):
            p = YouTubeProvider(api_key=None, cookies_file=None)
            assert p.enabled is False

    def test_cookies_content_materializes_temp_file(self):
        import os
        import tempfile as _tf
        content = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t0\tNAME\tVALUE\n"
        p = YouTubeProvider(cookies_content=content)
        assert p.cookies_file is not None
        assert p.cookies_file.startswith(_tf.gettempdir())
        assert os.path.isfile(p.cookies_file)
        with open(p.cookies_file, encoding="utf-8") as fh:
            assert fh.read() == content
        # 0o600 so the file is not world-readable inside the container
        mode = os.stat(p.cookies_file).st_mode & 0o777
        assert mode == 0o600
        os.unlink(p.cookies_file)


class TestGetInfo:
    def test_data_api_path(self):
        p = YouTubeProvider(api_key="AIza-test")
        snippet = {
            "title": "Never Gonna Give You Up",
            "channelTitle": "Rick Astley",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}},
        }
        content = {"duration": "PT3M33S"}
        items = [{"snippet": snippet, "contentDetails": content}]
        with patch.object(p, "_data_api_video", AsyncMock(return_value={
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "duration": content["duration"],
            "thumbnail": snippet["thumbnails"]["high"]["url"],
        })) as m:
            import asyncio
            meta = asyncio.get_event_loop().run_until_complete(
                p.get_info("dQw4w9WgXcQ")
            )
            m.assert_awaited_once_with("dQw4w9WgXcQ")
        assert meta.title == "Never Gonna Give You Up"
        assert meta.artist == "Rick Astley"
        assert meta.duration_seconds == 213
        assert meta.provider == "yt"

    def test_ytdlp_fallback(self):
        p = YouTubeProvider(api_key=None)
        info = {
            "title": "Fallback Title",
            "channel": "Fallback Channel",
            "duration": 240,
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
        }
        with patch.object(
            p, "_data_api_video", AsyncMock(return_value=None)
        ), patch.object(p, "_ytdlp_dump_json", AsyncMock(return_value=info)):
            import asyncio
            meta = asyncio.get_event_loop().run_until_complete(
                p.get_info("dQw4w9WgXcQ")
            )
        assert meta.title == "Fallback Title"
        assert meta.duration_seconds == 240

    def test_not_found(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_data_api_video", AsyncMock(return_value=None)
        ), patch.object(p, "_ytdlp_dump_json", AsyncMock(return_value=None)):
            import asyncio
            with pytest.raises(MediaNotFoundError):
                asyncio.get_event_loop().run_until_complete(
                    p.get_info("dQw4w9WgXcQ")
                )


class TestGetStream:
    def test_returns_direct_url(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/audio.mp3?sig=abc")),
        ):
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream("dQw4w9WgXcQ")
            )
        assert src.direct_url == "https://cdn.up.test/audio.mp3?sig=abc"
        assert src.mime_type == "audio/mpeg"

    def test_unavailable_raises(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(p, "_ytdlp_info_and_url", AsyncMock(return_value=None)):
            import asyncio
            with pytest.raises(ProviderUnavailableError):
                asyncio.get_event_loop().run_until_complete(
                    p.get_stream("dQw4w9WgXcQ")
                )


class TestGetStreamByType:
    def test_video_returns_video_mime(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/video.mp4?sig=abc")),
        ) as m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "video")
            )
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            media_type="video",
        )
        assert src.direct_url == "https://cdn.up.test/video.mp4?sig=abc"
        assert src.mime_type == "video/mp4"

    def test_audio_is_default(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/audio.m4a?sig=abc")),
        ) as m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ")
            )
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            media_type="audio",
        )
        assert src.mime_type == "audio/mpeg"

    def test_unknown_kind_falls_back_to_audio(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/audio.m4a")),
        ) as m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "bogus")
            )
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            media_type="audio",
        )
        assert src.mime_type == "audio/mpeg"

    def test_get_stream_delegates_to_audio(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/audio.m4a")),
        ) as m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream("dQw4w9WgXcQ")
            )
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            media_type="audio",
        )
        assert src.mime_type == "audio/mpeg"

    def test_stream_url_cached_across_calls(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/a.m4a?sig=abc")),
        ) as m:
            import asyncio
            loop = asyncio.get_event_loop()
            src1 = loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ"))
            src2 = loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ"))
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            media_type="audio",
        )
        assert src1.direct_url == src2.direct_url == "https://cdn.up.test/a.m4a?sig=abc"

    def test_invalidate_stream_forces_re_resolve(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=({"title": "T"}, "https://cdn.up.test/a.m4a?sig=abc")),
        ) as m:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ"))
            loop.run_until_complete(p.invalidate_stream("yt:dQw4w9WgXcQ"))
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ"))
        assert m.await_count == 2

    def test_audio_cache_does_not_leak_into_video(self):
        # Regression: an earlier audio resolution cached the muxed
        # audio URL under the bare video id; a later video request
        # (whose DASH pick fell through to the merged path) must NOT
        # revive that audio URL — kinds are cached independently.
        p = YouTubeProvider(api_key=None)

        async def fake(target, media_type="audio"):
            url = ("https://cdn.up.test/aud.m4a"
                   if media_type == "audio"
                   else "https://cdn.up.test/vid.mp4")
            return ({"title": "T"}, url)

        with patch.object(p, "_ytdlp_info_and_url",
                          AsyncMock(side_effect=fake)):
            import asyncio
            loop = asyncio.get_event_loop()
            aud = loop.run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "audio")
            )
            vid = loop.run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "video")
            )
            aud2 = loop.run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "audio")
            )
        assert aud.direct_url == "https://cdn.up.test/aud.m4a"
        assert vid.direct_url == "https://cdn.up.test/vid.mp4"
        assert aud2.direct_url == aud.direct_url
        assert vid.mime_type == "video/mp4"

    def test_invalidate_stream_clears_both_kinds(self):
        p = YouTubeProvider(api_key=None)

        async def fake(target, media_type="audio"):
            return ({"title": "T"}, f"https://cdn.up.test/{media_type}.m4a")

        with patch.object(p, "_ytdlp_info_and_url",
                          AsyncMock(side_effect=fake)) as m:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ", "audio"))
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ", "video"))
            before = m.await_count
            loop.run_until_complete(p.invalidate_stream("yt:dQw4w9WgXcQ"))
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ", "audio"))
            loop.run_until_complete(p.get_stream_by_type("dQw4w9WgXcQ", "video"))
        assert m.await_count == before + 2  # both re-resolved after invalidate


class TestSearch:
    def test_data_api_first(self):
        p = YouTubeProvider(api_key="AIza-test")
        items = [
            {"id": "dQw4w9WgXcQ", "title": "T1", "channel": "C1", "duration": None,
             "thumbnail": "https://x.test/1.jpg"},
        ]
        with patch.object(p, "_data_api_search", AsyncMock(return_value=items)), \
             patch.object(p, "_ytdlp_search", AsyncMock(return_value=[])) as yt:
            import asyncio
            out = asyncio.get_event_loop().run_until_complete(
                p.search("rick astley", limit=5)
            )
            yt.assert_not_awaited()
        assert len(out) == 1
        assert out[0].media_id == "dQw4w9WgXcQ"

    def test_ytdlp_fallback(self):
        p = YouTubeProvider(api_key=None)
        items = [
            {"id": "dQw4w9WgXcQ", "title": "T1", "channel": "C1", "duration": 213,
             "thumbnail": "https://x.test/1.jpg"},
        ]
        with patch.object(p, "_data_api_search", AsyncMock(return_value=[])), \
             patch.object(p, "_ytdlp_search", AsyncMock(return_value=items)):
            import asyncio
            out = asyncio.get_event_loop().run_until_complete(
                p.search("rick astley", limit=5)
            )
        assert len(out) == 1
        assert out[0].duration_seconds == 213

    def test_empty_query(self):
        p = YouTubeProvider(api_key="AIza-test")
        import asyncio
        assert asyncio.get_event_loop().run_until_complete(p.search("")) == []
        assert asyncio.get_event_loop().run_until_complete(p.search("   ")) == []


class TestDurationParsing:
    @pytest.mark.parametrize("raw,expected", [
        (None, None),
        (213, 213),
        (213.0, 213),
        ("213", 213),
        ("PT3M33S", 213),
        ("PT1H2M3S", 3723),
        ("3:33", 213),
        ("1:02:03", 3723),
        ("bogus", None),
    ])
    def test_parse_duration_seconds(self, raw, expected):
        from app.services.youtube_provider import _parse_duration_seconds
        assert _parse_duration_seconds(raw) == expected


class TestDashVideo:
    def test_dash_returns_split_streams(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_video_dash",
            AsyncMock(return_value=(
                {"title": "T"},
                "https://cdn.up.test/video-only.mp4?sig=v",
                "https://cdn.up.test/audio-only.m4a?sig=a",
                1080,
            )),
        ) as m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type(
                    "dQw4w9WgXcQ", "video", prefer_dash=True
                )
            )
        m.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", max_height=None
        )
        assert src.is_dash is True
        assert src.direct_url == "https://cdn.up.test/video-only.mp4?sig=v"
        assert src.direct_url_audio == "https://cdn.up.test/audio-only.m4a?sig=a"
        assert src.mime_type == "video/mp4"

    def test_dash_below_ceiling_falls_back_to_merged(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_video_dash",
            AsyncMock(return_value=(
                {"title": "T"},
                "https://cdn.up.test/v.mp4",
                "https://cdn.up.test/a.m4a",
                720,
            )),
        ), patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=(
                {"title": "T"}, "https://cdn.up.test/merged.mp4"
            )),
        ) as info_m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type(
                    "dQw4w9WgXcQ", "video", prefer_dash=True
                )
            )
        info_m.assert_awaited_once()
        assert src.is_dash is False
        assert src.direct_url == "https://cdn.up.test/merged.mp4"

    def test_dash_unavailable_falls_back_to_merged(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_video_dash", AsyncMock(return_value=None)
        ), patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=(
                {"title": "T"}, "https://cdn.up.test/merged.mp4"
            )),
        ) as info_m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type(
                    "dQw4w9WgXcQ", "video", prefer_dash=True
                )
            )
        info_m.assert_awaited_once()
        assert src.is_dash is False

    def test_dash_not_used_for_audio(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=(
                {"title": "T"}, "https://cdn.up.test/a.m4a"
            )),
        ) as info_m, patch.object(
            p, "_ytdlp_video_dash", AsyncMock(return_value=None)
        ) as dash_m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type(
                    "dQw4w9WgXcQ", "audio", prefer_dash=True
                )
            )
        info_m.assert_awaited_once()
        dash_m.assert_not_awaited()
        assert src.is_dash is False

    def test_video_without_prefer_dash_uses_merged(self):
        p = YouTubeProvider(api_key=None)
        with patch.object(
            p, "_ytdlp_info_and_url",
            AsyncMock(return_value=(
                {"title": "T"}, "https://cdn.up.test/v.mp4"
            )),
        ) as info_m, patch.object(
            p, "_ytdlp_video_dash", AsyncMock(return_value=None)
        ) as dash_m:
            import asyncio
            src = asyncio.get_event_loop().run_until_complete(
                p.get_stream_by_type("dQw4w9WgXcQ", "video")
            )
        info_m.assert_awaited_once()
        dash_m.assert_not_awaited()
        assert src.is_dash is False


class TestPickDashFormats:
    @staticmethod
    def _info():
        return {"formats": [
            # merged (video+audio) — ignored for DASH selection
            {"format_id": "18", "vcodec": "avc1.42001E", "acodec": "mp4a.40.2",
             "height": 360, "width": 640, "ext": "mp4", "url": "https://x/m.mp4"},
            # video-only
            {"format_id": "137", "vcodec": "avc1.640028", "acodec": "none",
             "height": 1080, "width": 1920, "ext": "mp4", "url": "https://x/v1080.mp4"},
            {"format_id": "313", "vcodec": "vp9", "acodec": "none",
             "height": 2160, "width": 3840, "ext": "webm", "url": "https://x/v4k.webm"},
            {"format_id": "4320", "vcodec": "av01.0.01M.08", "acodec": "none",
             "height": 4320, "width": 7680, "ext": "webm", "url": "https://x/v8k.webm"},
            # audio-only
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2",
             "abr": 128, "ext": "m4a", "url": "https://x/a128.m4a"},
            {"format_id": "251", "vcodec": "none", "acodec": "opus",
             "abr": 160, "ext": "webm", "url": "https://x/a160.webm"},
        ]}

    def test_selects_highest_video_and_audio(self):
        video, audio = _pick_dash_formats(self._info(), max_height=0)
        assert video["format_id"] == "4320"   # 8K, best available
        assert audio["format_id"] == "251"    # highest abr (160)

    def test_respects_max_height(self):
        video, audio = _pick_dash_formats(self._info(), max_height=2160)
        assert video["format_id"] == "313"    # 4K (highest <= 2160)
        assert audio["format_id"] == "251"

    def test_prefers_mp4_on_resolution_tie(self):
        info = {"formats": [
            {"format_id": "v1", "vcodec": "vp9", "acodec": "none",
             "height": 1080, "width": 1920, "ext": "webm", "url": "https://x/v.webm"},
            {"format_id": "v2", "vcodec": "avc1", "acodec": "none",
             "height": 1080, "width": 1920, "ext": "mp4", "url": "https://x/v.mp4"},
            {"format_id": "a", "vcodec": "none", "acodec": "opus",
             "abr": 128, "ext": "webm", "url": "https://x/a.webm"},
        ]}
        video, _ = _pick_dash_formats(info, 0)
        assert video["format_id"] == "v2"     # mp4 preferred at equal resolution

    def test_cap_above_available_returns_none(self):
        # only 1080/4K/8K video-only exist; a 720 cap fits none
        assert _pick_dash_formats(self._info(), max_height=720) is None

    def test_no_dash_returns_none(self):
        info = {"formats": [
            {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a",
             "height": 360, "url": "https://x/m.mp4"},
        ]}
        assert _pick_dash_formats(info, 0) is None
