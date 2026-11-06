"""Tests of the shared yt-dlp dump cache and the audio stream picker."""

from __future__ import annotations

import json

import pytest

from app.services.youtube_provider import (
    YouTubeProvider,
    _pick_audio_url,
    _run_ytdlp,
    _YtdlpResult,
)


def _dump_with_formats() -> dict:
    return {
        "id": "abc12345678",
        "title": "A Song",
        "duration": 212,
        "formats": [
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "abr": 128,
                "url": "https://cdn.example/audio-128.m4a",
                "protocol": "https",
            },
            {
                "format_id": "251",
                "ext": "webm",
                "vcodec": "none",
                "acodec": "opus",
                "abr": 160,
                "url": "https://cdn.example/audio-160.webm",
                "protocol": "https",
            },
            {
                "format_id": "137",
                "ext": "mp4",
                "vcodec": "avc1.640028",
                "acodec": "none",
                "url": "https://cdn.example/video-1080.mp4",
                "protocol": "https",
            },
            {
                "format_id": "hls-91",
                "ext": "mp4",
                "vcodec": "avc1.640028",
                "acodec": "none",
                "url": "https://cdn.example/manifest.m3u8",
                "protocol": "m3u8_native",
            },
        ],
    }


class TestPickAudioUrl:
    def test_m4a_wins_over_a_higher_bitrate_webm(self):
        url = _pick_audio_url(_dump_with_formats())
        assert url == "https://cdn.example/audio-128.m4a"

    def test_manifest_is_not_returned(self):
        info = {
            "formats": [
                {
                    "format_id": "hls",
                    "ext": "mp4",
                    "vcodec": "none",
                    "acodec": "mp4a.40.2",
                    "abr": 160,
                    "url": "https://cdn.example/only.m3u8",
                    "protocol": "m3u8_native",
                }
            ]
        }
        assert _pick_audio_url(info) is None

    def test_no_audio_formats(self):
        info = {
            "formats": [
                {
                    "format_id": "137",
                    "ext": "mp4",
                    "vcodec": "avc1.640028",
                    "acodec": "none",
                    "url": "https://cdn.example/video.mp4",
                    "protocol": "https",
                }
            ]
        }
        assert _pick_audio_url(info) is None

    def test_empty_dump(self):
        assert _pick_audio_url({}) is None


class TestDumpCache:
    """The metadata of a video and its DASH split come out of one dump."""

    @pytest.mark.asyncio
    async def test_split_reuses_the_dump_of_the_metadata(self, monkeypatch):
        calls = {"dump": 0, "split": 0}

        async def fake_run(*args, timeout=None):
            calls["dump"] += 1
            return _YtdlpResult(
                ok=True, data=json.dumps(_dump_with_formats()).encode("utf-8")
            )

        monkeypatch.setattr(
            "app.services.youtube_provider._run_ytdlp", fake_run
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._resolve_ytdlp_argv",
            lambda *args, **kwargs: ["yt-dlp"],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._cookies_args",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._js_runtime_args",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._proxy_args",
            lambda *args, **kwargs: [],
        )

        provider = YouTubeProvider.__new__(YouTubeProvider)
        YouTubeProvider.__init__(provider)

        target = "https://www.youtube.com/watch?v=abc12345678"
        # The metadata lookup pays for the extraction.
        await provider._ytdlp_dump_json(target)
        # The split lookup must not run a second extraction.
        await provider._ytdlp_video_split_once(target, max_height=720)

        assert calls["dump"] == 1
        assert calls["split"] == 0

    @pytest.mark.asyncio
    async def test_audio_url_comes_from_the_cached_dump(self, monkeypatch):
        calls = {"dump": 0}

        async def fake_run(*args, timeout=None):
            calls["dump"] += 1
            return _YtdlpResult(
                ok=True, data=json.dumps(_dump_with_formats()).encode("utf-8")
            )

        monkeypatch.setattr(
            "app.services.youtube_provider._run_ytdlp", fake_run
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._resolve_ytdlp_argv",
            lambda *args, **kwargs: ["yt-dlp"],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._cookies_args",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._js_runtime_args",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            "app.services.youtube_provider._proxy_args",
            lambda *args, **kwargs: [],
        )

        provider = YouTubeProvider.__new__(YouTubeProvider)
        YouTubeProvider.__init__(provider)

        target = "https://www.youtube.com/watch?v=abc12345678"
        await provider._ytdlp_dump_json(target)
        result = await provider._ytdlp_info_and_url_once(target, "audio")

        assert result is not None
        assert result[1] == "https://cdn.example/audio-128.m4a"
        assert calls["dump"] == 1
