import pytest

import app.services.youtube_provider as yp
from app.services.youtube_provider import _YtdlpResult, _run_ytdlp


@pytest.mark.asyncio
async def test_android_retry_on_attestation_error(monkeypatch):
    calls = []
    boom = _YtdlpResult(ok=False, stderr="ERROR: [youtube] x: The page needs to be reloaded.")

    async def fake_once(argv, timeout):
        calls.append(argv)
        if "--extractor-args" in argv:
            return _YtdlpResult(ok=True, data=b'{"id": "x"}')
        return boom

    monkeypatch.setattr(yp, "_ytdlp_once", fake_once)
    monkeypatch.setattr(yp, "_resolve_ytdlp_argv", lambda: ["yt-dlp"])
    res = await _run_ytdlp("--dump-json", "https://www.youtube.com/watch?v=x")
    assert res.ok
    assert len(calls) == 2
    assert "youtube:player_client=android" in calls[1]


@pytest.mark.asyncio
async def test_no_retry_on_other_errors(monkeypatch):
    calls = []

    async def fake_once(argv, timeout):
        calls.append(argv)
        return _YtdlpResult(ok=False, stderr="yt-dlp timeout")

    monkeypatch.setattr(yp, "_ytdlp_once", fake_once)
    monkeypatch.setattr(yp, "_resolve_ytdlp_argv", lambda: ["yt-dlp"])
    res = await _run_ytdlp("--dump-json", "url")
    assert not res.ok
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_no_retry_when_client_args_already_given(monkeypatch):
    calls = []

    async def fake_once(argv, timeout):
        calls.append(argv)
        return _YtdlpResult(ok=False, stderr="Sign in to confirm you're not a bot")

    monkeypatch.setattr(yp, "_ytdlp_once", fake_once)
    monkeypatch.setattr(yp, "_resolve_ytdlp_argv", lambda: ["yt-dlp"])
    await _run_ytdlp("--dump-json", "--extractor-args", "youtube:player_client=tv", "url")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retry_strips_cookies(monkeypatch):
    calls = []

    async def fake_once(argv, timeout):
        calls.append(argv)
        if "--extractor-args" in argv:
            assert "--cookies" not in argv
            return _YtdlpResult(ok=True, data=b"{}")
        return _YtdlpResult(ok=False, stderr="The page needs to be reloaded")

    monkeypatch.setattr(yp, "_ytdlp_once", fake_once)
    monkeypatch.setattr(yp, "_resolve_ytdlp_argv", lambda: ["yt-dlp"])
    res = await _run_ytdlp("--cookies", "/tmp/ck.txt", "url")
    assert res.ok and len(calls) == 2
    assert "--cookies" not in calls[1]
