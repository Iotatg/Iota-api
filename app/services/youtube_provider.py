"""YouTube media provider.

Resolves YouTube video ids (`yt:<11-char-id>`) into metadata and a streamable
direct URL. Uses ``yt-dlp`` as a subprocess so the app still boots without
``yt-dlp`` installed; falls back to the YouTube Data API v3 when
``YOUTUBE_API_KEY`` is set.

The provider is intentionally narrow — it implements the three MediaProvider
abstract methods (search, get_info, get_stream) and nothing else. Related-
suggestions, radio mix, and the Innertube engine live in the sibling bot
trees (IotaXMedia / iotaxmedia-beta) and are out of scope here.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import httpx

from app.config import get_settings
from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    ProviderUnavailableError,
    StreamSource,
)
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from app.services.stream_cache import StreamCacheService

logger = get_logger(__name__)

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_WATCH = "https://www.youtube.com/watch?v={vid}"
_DATA_API_BASE = "https://www.googleapis.com/youtube/v3"
_YTDLP_TIMEOUT = 25.0
_TRANSCRIPT_TIMEOUT = 60.0
_TRANSCRIPT_TTL = 3600.0
_TRANSCRIPT_CACHE_MAX = 100
_TRANSCRIPT_LANG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,15}$")
_VTT_TS_RE = re.compile(r"(\d+:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?")
_VTT_TAG_RE = re.compile(r"<[^>]+>")
# YouTube serves video above this height only as separate
# DASH streams (video-only + audio-only). At or below it a
# single merged file is available, which is seekable and
# needs no remux, so DASH is only worth it above this line.
_MERGED_VIDEO_CEILING = 720


def _resolve_ytdlp_argv() -> List[str]:
    """Return the argv prefix that invokes yt-dlp.

    Uses ``python3 -m yt_dlp`` so the same Python environment is used; the
    raw ``yt-dlp`` script may live in a different venv or be missing on PATH.
    """
    py = shutil.which("python3") or shutil.which("python")
    if py:
        return [py, "-m", "yt_dlp"]
    fallback = shutil.which("yt-dlp")
    if fallback:
        return [fallback]
    return []


def _cookies_args(cookies_file: Optional[str]) -> List[str]:
    if not cookies_file:
        return []
    if not os.path.isfile(cookies_file):
        return []
    return ["--cookies", cookies_file]


def _proxy_args(proxy: Optional[str]) -> List[str]:
    if not proxy:
        return []
    return ["--proxy", proxy]


def _js_runtime_args() -> List[str]:
    """Prefer a system JS runtime for YouTube signature solving (EJS).

    yt-dlp's default runtime is deno; node and quickjs must be requested
    explicitly. Use the first available so the "n" challenge can be solved.
    With a runtime present, also opt into the yt-dlp-ejs remote components:
    they mint PO tokens, which is what actually lifts datacenter
    "Sign in to confirm you're not a bot" walls for most clients.
    """
    for runtime in ("deno", "node", "quickjs", "qjs"):
        path = shutil.which(runtime)
        if path:
            return ["--js-runtimes", f"{runtime}:{path}",
                    "--remote-components", "ejs:github"]
    return []


@dataclass
class _YtdlpResult:
    ok: bool
    data: Any = None
    stderr: str = ""


# Datacenter/web clients on flagged IPs hit YouTube attestation errors
# ("page needs to be reloaded", bot check) or format gaps; the cookie-less
# `android` client is served without attestation from these IPs, so retry
# once with it before giving up.
_YTDLP_RETRY_MARKERS = (
    "The page needs to be reloaded",
    "Sign in to confirm",
    "Requested format is not available",
)
# Formats the android client does not serve; let yt-dlp fall back within
# the same invocation (18 → 251/bestaudio).
_ANDROID_EXTRA_ARGS = ("-4", "--extractor-args", "youtube:player_client=android")

# ── Circuit breaker ─────────────────────────────────────────────────────
# A flagged datacenter IP answers every client with bot-check errors for
# hours. Repeated hammering prolongs the block, so after a few consecutive
# IP-level failures we fast-fail YouTube for a cooldown window; callers
# then get the player-client rotation in ``rotation_stream`` as a native
# failover. Recovered requests reset the streak, so a live IP trips the
# breaker at most once.
_BREAKER_MARKERS = (
    "Sign in to confirm",
    "HTTP Error 429",
    "The page needs to be reloaded",
)
_breaker_state = {"open_until": 0.0, "streak": 0}


def _breaker_config() -> tuple[int, int]:
    from app.config import get_settings
    s = get_settings()
    return s.youtube_breaker_threshold, s.youtube_breaker_cooldown_seconds


def breaker_is_open() -> bool:
    return time.monotonic() < _breaker_state["open_until"]


def breaker_reset() -> None:
    _breaker_state["open_until"] = 0.0
    _breaker_state["streak"] = 0


def _breaker_observe(result: _YtdlpResult) -> None:
    threshold, cooldown = _breaker_config()
    if threshold <= 0:
        return
    if result.ok:
        _breaker_state["streak"] = 0
        return
    if not any(m in result.stderr for m in _BREAKER_MARKERS):
        return  # per-video or local failure; not an IP-level block
    _breaker_state["streak"] += 1
    if _breaker_state["streak"] >= threshold:
        _breaker_state["open_until"] = time.monotonic() + cooldown
        _breaker_state["streak"] = 0
        logger.warning(
            "yt_circuit_open",
            extra={"cooldown_seconds": cooldown,
                   "cooldown_remaining": round(
                       _breaker_state["open_until"] - time.monotonic(), 1)},
        )


def _strip_cookies(args: List[str]) -> List[str]:
    """Drop ``--cookies <path>`` pairs; the android client ignores them but
    a session-flagged cookie file poisons its response (format-less payload).
    """
    out: List[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--cookies":
            skip = True
            continue
        if a.startswith("--cookies="):
            continue
        out.append(a)
    return out


async def _ytdlp_once(argv: List[str], timeout: float) -> _YtdlpResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as e:
        return _YtdlpResult(ok=False, stderr=str(e))
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return _YtdlpResult(ok=False, stderr="yt-dlp timeout")
    if proc.returncode != 0:
        return _YtdlpResult(ok=False, stderr=stderr.decode(errors="ignore"))
    return _YtdlpResult(ok=True, data=stdout)


async def _run_ytdlp(
    *args: str, timeout: float = _YTDLP_TIMEOUT, bypass_breaker: bool = False
) -> _YtdlpResult:
    """Run yt-dlp as an async subprocess; on attestation-style failures
    retry once via the cookie-less android player client.

    ``bypass_breaker`` runs the command even while the breaker is open
    (used for search feeds, which address a different endpoint and can
    survive an IP-level player block); its result never mutates breaker
    state so a doomed bypass cannot prolong the cooldown."""
    argv_prefix = _resolve_ytdlp_argv()
    if not argv_prefix:
        return _YtdlpResult(ok=False, stderr="yt-dlp not found on PATH")
    if breaker_is_open() and not bypass_breaker:
        return _YtdlpResult(
            ok=False,
            stderr="youtube circuit breaker open (IP bot-blocked; cooling down)",
        )
    argv = [*argv_prefix, *args]
    result = await _ytdlp_once(argv, timeout)
    if (
        not result.ok
        and "--extractor-args" not in args
        and any(m in result.stderr for m in _YTDLP_RETRY_MARKERS)
    ):
        logger.info("ytdlp_android_retry", extra={"reason": result.stderr.strip().splitlines()[-1:]})
        retry_argv = [*argv_prefix, *_strip_cookies(list(args)), *_ANDROID_EXTRA_ARGS]
        result2 = await _ytdlp_once(retry_argv, timeout)
        if result2.ok:
            result = result2
            if not bypass_breaker:
                _breaker_observe(result2)
                return result2
        result = result2
    if not bypass_breaker:
        _breaker_observe(result)
    return result


def _log_ytdlp_fail(op: str, target: str, stderr: str) -> None:
    """Surface yt-dlp failure reasons; silent ``return None`` hid the
    real upstream error (bot check, cookie expiry, JS runtime...)."""
    tail = (stderr or "").strip().splitlines()[-3:]
    logger.warning(
        "ytdlp_fail", extra={"op": op, "target": target, "stderr_tail": " | ".join(tail)}
    )


def _vtt_seconds(raw: str) -> float:
    """`00:01:02.500` (or `01:02.5`) -> seconds."""
    tail = _VTT_TS_RE.search(raw)
    stamp = (tail.group(0) if tail else raw).replace(",", ".")
    parts = stamp.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError:
        return 0.0


def parse_vtt(text: str) -> List[dict]:
    """WebVTT -> [{start_seconds, text}] with caption-window dedupe.

    Auto-generated tracks repeat each line across overlapping cues; a
    line identical to the previous emission within a few seconds is a
    window artifact, not a lyric repeat, so it is dropped.
    """
    segments: List[dict] = []
    prev_text = ""
    prev_start = -10.0
    for block in text.replace("\r", "").split("\n\n"):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines or "-->" not in "\n".join(lines):
            continue
        ts_line = next((ln for ln in lines if "-->" in ln), "")
        start = _vtt_seconds(ts_line.split("-->")[0])
        for ln in lines:
            if "-->" in ln or ln.startswith(
                ("WEBVTT", "Kind:", "Language:", "STYLE", "NOTE")
            ) or ln.endswith("}"):
                continue
            clean = re.sub(r"\s+", " ", _VTT_TAG_RE.sub("", ln)).strip()
            clean = clean.strip("♪ ").strip()
            if not clean or clean.startswith(("Kind:", "Language:", "Style", "NOTE")):
                continue
            if clean == prev_text and start - prev_start < 2.5:
                continue
            if re.fullmatch(r"\[[^\]]{1,60}\]|♪+", clean):
                continue
            segments.append({"start_seconds": round(start, 2), "text": clean})
            prev_text, prev_start = clean, start
    return segments


def _parse_duration_seconds(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.isdigit():
        return int(s)
    # ISO 8601: PT#H#M#S
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s)
    if m:
        h = int(m.group(1) or 0)
        mi = int(m.group(2) or 0)
        se = int(m.group(3) or 0)
        return h * 3600 + mi * 60 + se
    # HH:MM:SS or M:SS
    parts = s.split(":")
    if 1 <= len(parts) <= 3 and all(p.isdigit() for p in parts):
        nums = [int(p) for p in parts]
        while len(nums) < 3:
            nums.insert(0, 0)
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def _thumbnail(info: dict) -> str:
    thumb = info.get("thumbnail")
    if isinstance(thumb, str) and thumb:
        return thumb.split("?")[0]
    thumbs = info.get("thumbnails") or []
    if thumbs and isinstance(thumbs[-1], dict):
        url = thumbs[-1].get("url", "")
        if isinstance(url, str):
            return url.split("?")[0]
    return ""


def _stat(info: dict, key: str) -> Optional[int]:
    val = info.get(key)
    if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
        return int(val)
    return None


def _to_metadata(video_id: str, info: dict) -> MediaMetadata:
    return MediaMetadata(
        media_id=video_id,
        title=info.get("title") or video_id,
        artist=info.get("channel") or info.get("uploader") or info.get("channelTitle"),
        duration_seconds=_parse_duration_seconds(info.get("duration")),
        thumbnail_url=_thumbnail(info) or None,
        mime_type="audio/mpeg",
        storage_key="",
        provider="yt",
        views=_stat(info, "view_count"),
        likes=_stat(info, "like_count"),
    )


def _pick_dash_formats(
    info: dict, max_height: int
) -> Optional[Tuple[dict, dict]]:
    """Select ``(video_only, audio_only)`` formats from a yt-dlp info dict.

    YouTube serves resolutions above 720p only as separate DASH
    streams (a video-only stream plus a matching audio-only stream).
    This picks the highest-resolution video-only stream — optionally
    capped at ``max_height`` (``0`` means no cap, i.e. best available
    up to 8K) — plus the highest-bitrate audio-only stream. Returns
    ``None`` when the video exposes no separate DASH streams.
    """
    formats = info.get("formats") or []
    video_candidates: List[dict] = []
    audio_candidates: List[dict] = []
    for fmt in formats:
        if not isinstance(fmt, dict) or not fmt.get("url"):
            continue
        vcodec = str(fmt.get("vcodec") or "none")
        acodec = str(fmt.get("acodec") or "none")
        if vcodec != "none" and acodec == "none":
            video_candidates.append(fmt)
        elif acodec != "none" and vcodec == "none":
            audio_candidates.append(fmt)
    if not video_candidates or not audio_candidates:
        return None

    def _res(f: dict) -> Tuple[int, int]:
        return (int(f.get("height") or 0), int(f.get("width") or 0))

    pool = video_candidates
    if max_height and max_height > 0:
        capped = [f for f in pool if int(f.get("height") or 0) <= max_height]
        if not capped:
            # Nothing at or under the requested ceiling: no
            # DASH representation fits, so the caller falls
            # back to the merged (single-file) stream.
            return None
        pool = capped
    # Highest resolution wins; on an exact tie prefer the mp4
    # container (h.264) for the widest player compatibility.
    video = max(pool, key=lambda f: (_res(f), f.get("ext") == "mp4"))

    def _abr(f: dict) -> int:
        for key in ("abr", "bitrate"):
            val = f.get(key)
            if isinstance(val, (int, float)):
                return int(val)
        return 0

    audio = max(audio_candidates, key=_abr)
    return video, audio


class YouTubeProvider(MediaProvider):
    """YouTube provider using yt-dlp + optional Data API v3 fallback."""

    name = "yt"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookies_file: Optional[str] = None,
        cookies_content: Optional[str] = None,
        proxy: Optional[str] = None,
        ytdlp_path: Optional[str] = None,
        stream_cache: Optional["StreamCacheService"] = None,
    ) -> None:
        self.api_key = api_key
        self.proxy = proxy
        self._ytdlp_argv = ytdlp_path.split() if ytdlp_path else _resolve_ytdlp_argv()
        # If cookies_content is provided (e.g. from an env var on a host
        # like Railway where uploading a file is awkward), materialize it
        # to a temp file at provider construction. The file lives in the
        # container's ephemeral filesystem and is recreated on every
        # restart; this avoids committing cookies to the image.
        if cookies_content:
            path = os.path.join(tempfile.gettempdir(), "iotatg_yt_cookies.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(cookies_content)
            os.chmod(path, 0o600)
            self.cookies_file = path
        else:
            self.cookies_file = cookies_file
        # In-memory metadata cache. Video metadata rarely changes, so a
        # short TTL lets repeat lookups (info/stream/download of the same
        # song) skip a second yt-dlp invocation.
        self._info_cache: dict[str, Tuple[float, MediaMetadata]] = {}
        self._info_cache_ttl = float(get_settings().metadata_cache_ttl or 0)
        # Resolved stream-URL cache. YouTube CDN URLs are valid
        # for hours, so a short TTL lets repeat plays of the
        # same song skip the multi-second yt-dlp extraction.
        # Stores (expiry, url, metadata) so a hit also warms the
        # metadata cache. The in-memory dict is the hot layer;
        # the optional StreamCacheService is the persistent layer
        # (survives a restart) and is effectively unlimited.
        self._stream_cache: dict[str, Tuple[float, str, MediaMetadata]] = {}
        self._stream_cache_ttl = float(get_settings().stream_cache_ttl or 0)
        self._stream_cache_service = stream_cache
        self._stream_cache_persistent_ttl = float(
            get_settings().stream_cache_persistent_ttl or 0
        )
        # Caption payloads are stable and big-ish; keep a small capped
        # TTL map instead of hitting yt-dlp on every transcript request.
        self._transcript_cache: dict[str, Tuple[float, dict]] = {}

    def _cache_get(self, video_id: str) -> Optional[MediaMetadata]:
        if self._info_cache_ttl <= 0:
            return None
        hit = self._info_cache.get(video_id)
        if not hit:
            return None
        expires, meta = hit
        if time.monotonic() > expires:
            self._info_cache.pop(video_id, None)
            return None
        return meta

    def _cache_put(self, video_id: str, meta: MediaMetadata) -> None:
        if self._info_cache_ttl <= 0:
            return
        # Bound memory: drop expired entries when the cache grows large.
        if len(self._info_cache) >= 1000:
            now = time.monotonic()
            stale = [k for k, (exp, _) in self._info_cache.items() if exp <= now]
            for k in stale:
                self._info_cache.pop(k, None)
        self._info_cache[video_id] = (time.monotonic() + self._info_cache_ttl, meta)

    def _stream_cache_mem_get(
        self, video_id: str
    ) -> Optional[Tuple[str, MediaMetadata]]:
        if self._stream_cache_ttl <= 0:
            return None
        hit = self._stream_cache.get(video_id)
        if not hit:
            return None
        expires, url, meta = hit
        if time.monotonic() > expires:
            self._stream_cache.pop(video_id, None)
            return None
        return url, meta

    def _stream_cache_mem_put(self, video_id: str, url: str, meta: MediaMetadata) -> None:
        if self._stream_cache_ttl <= 0:
            return
        # No hard count limit — the persistent (database) cache is
        # unlimited. This safety valve only purges already-expired
        # entries if the hot layer ever grows very large, so live
        # entries are never dropped by count.
        if len(self._stream_cache) >= 50_000:
            now = time.monotonic()
            stale = [k for k, (exp, _, _) in self._stream_cache.items() if exp <= now]
            for k in stale:
                self._stream_cache.pop(k, None)
        self._stream_cache[video_id] = (
            time.monotonic() + self._stream_cache_ttl, url, meta
        )

    async def _stream_cache_get(
        self, video_id: str
    ) -> Optional[Tuple[str, MediaMetadata]]:
        # Hot layer first (no I/O).
        hit = self._stream_cache_mem_get(video_id)
        if hit is not None:
            return hit
        # Persistent layer (survives a restart).
        if self._stream_cache_service is not None:
            try:
                hit = await self._stream_cache_service.get(video_id)
            except Exception as e:
                logger.warning(
                    "stream_cache_get_error", extra={"err": str(e)}
                )
                hit = None
            if hit is not None:
                url, meta = hit
                self._stream_cache_mem_put(video_id, url, meta)
                return url, meta
        return None

    async def _stream_cache_put(self, video_id: str, url: str, meta: MediaMetadata) -> None:
        self._stream_cache_mem_put(video_id, url, meta)
        if self._stream_cache_service is not None and self._stream_cache_persistent_ttl > 0:
            try:
                await self._stream_cache_service.put(
                    video_id, url, meta, ttl=self._stream_cache_persistent_ttl
                )
            except Exception as e:
                logger.warning(
                    "stream_cache_put_error", extra={"err": str(e)}
                )

    async def invalidate_stream(self, media_id: str) -> None:
        """Drop a cached stream URL so the next request re-resolves.

        Called when an upstream URL fails (e.g. revoked before
        its TTL) so a single bad URL does not poison the cache.
        Accepts the full ``yt:<id>`` form or the bare id.
        """
        video_id = media_id
        prefix = f"{self.name}:"
        if video_id.startswith(prefix):
            video_id = video_id[len(prefix):]
        # Drop every representation of this id: the current kind-scoped
        # keys and the legacy bare key written before the split.
        keys = (video_id, f"{video_id}:audio", f"{video_id}:video")
        for key in keys:
            self._stream_cache.pop(key, None)
        if self._stream_cache_service is not None:
            for key in keys:
                try:
                    await self._stream_cache_service.invalidate(key)
                except Exception as e:
                    logger.warning(
                        "stream_cache_invalidate_error",
                        extra={"err": str(e)},
                    )

    @property
    def enabled(self) -> bool:
        """Provider is enabled when we can actually fetch something."""
        if self.api_key:
            return True
        if self.cookies_file and os.path.isfile(self.cookies_file):
            return True
        # yt-dlp with no cookies can still work for some videos; allow if binary exists
        return bool(self._ytdlp_argv)

    @staticmethod
    def validate_id(video_id: str) -> str:
        """Return the canonical 11-char id or raise MediaNotFoundError."""
        if not video_id or not _YOUTUBE_ID_RE.fullmatch(video_id):
            raise MediaNotFoundError(f"invalid youtube video id: {video_id!r}")
        return video_id

    def _watch_url(self, video_id: str) -> str:
        return _YOUTUBE_WATCH.format(vid=video_id)

    async def _data_api_video(self, video_id: str) -> Optional[dict]:
        if not self.api_key:
            return None
        params = {
            "id": video_id,
            "part": "snippet,contentDetails",
            "key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{_DATA_API_BASE}/videos", params=params)
            if resp.status_code != 200:
                return None
            items = (resp.json() or {}).get("items") or []
            if not items:
                return None
            item = items[0]
            snippet = item.get("snippet") or {}
            content = item.get("contentDetails") or {}
            thumbs = snippet.get("thumbnails") or {}
            thumb = (thumbs.get("high") or thumbs.get("default") or {}).get("url", "")
            return {
                "title": snippet.get("title"),
                "channel": snippet.get("channelTitle"),
                "duration": content.get("duration"),
                "thumbnail": thumb,
            }
        except Exception as e:
            logger.warning("youtube_data_api_video_error", extra={"err": str(e)})
            return None

    async def _data_api_search(self, query: str, limit: int) -> List[dict]:
        if not self.api_key:
            return []
        params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": str(min(limit, 50)),
            "key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{_DATA_API_BASE}/search", params=params)
            if resp.status_code != 200:
                return []
            out: List[dict] = []
            for item in (resp.json() or {}).get("items") or []:
                vid = ((item.get("id") or {}).get("videoId")) or ""
                if not _YOUTUBE_ID_RE.fullmatch(vid):
                    continue
                snippet = item.get("snippet") or {}
                out.append({
                    "id": vid,
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "duration": None,
                    "thumbnail": ((snippet.get("thumbnails") or {}).get("high") or {}).get("url", ""),
                })
            return out
        except Exception as e:
            logger.warning("youtube_data_api_search_error", extra={"err": str(e)})
            return []

    async def _ytdlp_dump_json(self, target: str) -> Optional[dict]:
        if not self._ytdlp_argv:
            return None
        args = [
            "--dump-json",
            "--no-warnings",
            "--no-update",
            "--skip-download",
            "--socket-timeout", "20",
            *_cookies_args(self.cookies_file),
            *_js_runtime_args(),
            *_proxy_args(self.proxy),
            target,
        ]
        result = await _run_ytdlp(*args)
        if not result.ok or not result.data:
            _log_ytdlp_fail("dump", target, result.stderr)
            return None
        try:
            first_line = result.data.decode(errors="ignore").splitlines()[0]
            return json.loads(first_line)
        except Exception:
            return None

    async def _ytdlp_info_and_url(
        self, target: str, media_type: str
    ) -> Optional[Tuple[dict, str]]:
        """One ``--dump-json`` call returning ``(info_dict, direct_url)``.

        Combining the metadata and URL lookups into a single yt-dlp
        invocation halves the per-download latency: the top-level
        ``url`` field honours ``-f`` (so it is the selected audio or
        video stream), and the same payload carries title/artist/
        duration for the metadata cache.
        """
        if not self._ytdlp_argv:
            return None
        if media_type == "video":
            fmt = (
                "best[height<=?720][width<=?1280]"
                "/bestvideo[height<=?720][width<=?1280]"
                "/bestvideo"
            )
        else:
            fmt = "bestaudio[ext=m4a]/bestaudio/best"
        args = [
            "--dump-json",
            "-f", fmt,
            "--no-warnings",
            "--no-update",
            "--socket-timeout", "20",
            *_cookies_args(self.cookies_file),
            *_js_runtime_args(),
            *_proxy_args(self.proxy),
            target,
        ]
        result = await _run_ytdlp(*args)
        if not result.ok or not result.data:
            _log_ytdlp_fail("dump", target, result.stderr)
            return None
        try:
            first_line = result.data.decode(errors="ignore").splitlines()[0]
            info = json.loads(first_line)
        except Exception:
            return None
        url = info.get("url")
        if not url or not str(url).startswith("http"):
            return None
        return info, url

    async def _ytdlp_video_dash(
        self, target: str, max_height: Optional[int] = None
    ) -> Optional[Tuple[dict, str, str]]:
        """Resolve the best DASH video + audio streams.

        One ``--dump-json`` call (no ``-f``) returns every
        format; ``_pick_dash_formats`` then selects the best
        video-only and audio-only streams for a high-quality
        (1080p / 4K / 8K) download. Returns
        ``(info, video_url, audio_url, video_height)``.
        """
        if not self._ytdlp_argv:
            return None
        args = [
            "--dump-json",
            "--no-warnings",
            "--no-update",
            "--socket-timeout", "20",
            *_cookies_args(self.cookies_file),
            *_js_runtime_args(),
            *_proxy_args(self.proxy),
            target,
        ]
        result = await _run_ytdlp(*args)
        if not result.ok or not result.data:
            _log_ytdlp_fail("dump", target, result.stderr)
            return None
        try:
            info = json.loads(
                result.data.decode(errors="ignore").splitlines()[0]
            )
        except Exception:
            return None
        if max_height is None:
            max_height = int(get_settings().youtube_video_max_height or 0)
        else:
            max_height = max(0, int(max_height))
        picked = _pick_dash_formats(info, max_height)
        if not picked:
            return None
        video_fmt, audio_fmt = picked
        video_url = video_fmt.get("url")
        audio_url = audio_fmt.get("url")
        if not video_url or not audio_url:
            return None
        return info, video_url, audio_url, int(video_fmt.get("height") or 0)

    async def _ytdlp_search(self, query: str, limit: int) -> List[dict]:
        return await self._ytdlp_flat_entries(f"ytsearch{limit}:{query}")

    async def _ytdlp_flat_entries(
        self, target: str, playlist_end: int = 0
    ) -> List[dict]:
        """One flat ``--dump-json`` invocation; works for ``ytsearchN:``
        targets, playlist URLs and the trending feed alike. Entries carry
        id/title/channel/duration/thumbnail/view_count."""
        if not self._ytdlp_argv:
            return []
        args = [
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            "--no-update",
            "--skip-download",
            "--socket-timeout", "20",
            *_cookies_args(self.cookies_file),
            *_js_runtime_args(),
            *_proxy_args(self.proxy),
        ]
        if playlist_end > 0:
            args += ["--playlist-end", str(playlist_end)]
        # Feeds hit the search/innertube surface, which survives the
        # player-side bot wall via the tv client — resolve anyway and
        # keep the breaker untouched either way.
        forced = breaker_is_open()
        if forced:
            args += ["--extractor-args", "youtube:player_client=tv"]
            args = _strip_cookies(args)
        args.append(target)
        result = await _run_ytdlp(*args, bypass_breaker=forced)
        if not result.ok or not result.data:
            _log_ytdlp_fail("dump", target, result.stderr)
            return []
        out: List[dict] = []
        for line in result.data.decode(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            vid = obj.get("id") or ""
            if not _YOUTUBE_ID_RE.fullmatch(vid):
                continue
            out.append({
                "id": vid,
                "title": obj.get("title") or "",
                "channel": obj.get("channel") or obj.get("uploader") or "",
                "duration": obj.get("duration"),
                "thumbnail": _thumbnail(obj),
                "view_count": obj.get("view_count"),
            })
        return out

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        if not query or not query.strip():
            return []
        limit = max(1, min(limit, 50))
        # Data API first (fastest, quota-bounded), then yt-dlp.
        items = await self._data_api_search(query, limit)
        if not items:
            items = await self._ytdlp_search(query, limit)
        seen: set = set()
        out: List[MediaMetadata] = []
        for item in items:
            vid = item.get("id") or ""
            if not _YOUTUBE_ID_RE.fullmatch(vid) or vid in seen:
                continue
            seen.add(vid)
            out.append(MediaMetadata(
                media_id=vid,
                title=item.get("title") or vid,
                artist=item.get("channel") or None,
                duration_seconds=_parse_duration_seconds(item.get("duration")),
                thumbnail_url=item.get("thumbnail") or None,
                mime_type="audio/mpeg",
                storage_key="",
                provider=self.name,
                views=_stat(item, "view_count"),
                likes=_stat(item, "like_count"),
            ))
        return out[:limit]

    async def get_info(self, media_id: str) -> MediaMetadata:
        video_id = self.validate_id(media_id)
        cached = self._cache_get(video_id)
        if cached is not None:
            return cached
        info = await self._data_api_video(video_id)
        if info is None:
            info = await self._ytdlp_dump_json(self._watch_url(video_id))
        if info is None:
            raise MediaNotFoundError(f"youtube: no info for {video_id}")
        meta = _to_metadata(video_id, info)
        self._cache_put(video_id, meta)
        return meta

    async def get_stream(self, media_id: str) -> StreamSource:
        return await self.get_stream_by_type(media_id, "audio")

    async def get_stream_by_type(
        self,
        media_id: str,
        media_type: str = "audio",
        prefer_dash: bool = False,
        max_height: Optional[int] = None,
    ) -> StreamSource:
        video_id = self.validate_id(media_id)
        kind = media_type if media_type in ("audio", "video") else "audio"
        mime_type = "video/mp4" if kind == "video" else "audio/mpeg"
        # High-quality video: YouTube serves resolutions above
        # 720p only as separate DASH streams, so resolve the
        # best video-only + audio-only pair. The caller remuxes
        # them together with ffmpeg. DASH URLs are resolved
        # fresh (not served from the stream cache) because the
        # cached value is a merged single-file URL, which is a
        # different representation.
        if kind == "video" and prefer_dash:
            result = await self._ytdlp_video_dash(
                self._watch_url(video_id), max_height=max_height
            )
            # DASH only pays off when the best video-only
            # stream is above the merged (single-file)
            # ceiling; at or below it the merged stream is
            # seekable and needs no remux, so fall through
            # to the merged path below.
            if result is not None and result[3] > _MERGED_VIDEO_CEILING:
                info, video_url, audio_url, _height = result
                meta = _to_metadata(video_id, info)
                self._cache_put(video_id, meta)
                return StreamSource(
                    storage_key="",
                    size_bytes=0,  # size is only known after the merge
                    mime_type=mime_type,
                    direct_url=video_url,
                    direct_url_audio=audio_url,
                    is_dash=True,
                )
        # Cache hit: reuse the resolved CDN URL and metadata,
        # skipping the multi-second yt-dlp extraction. The key
        # is kind-scoped: an audio request must never revive the
        # muxed video URL (or vice versa), as they are different
        # representations of the same video id.
        cache_key = f"{video_id}:{kind}"
        cached = await self._stream_cache_get(cache_key)
        if cached is not None:
            url, meta = cached
            self._cache_put(video_id, meta)
            return StreamSource(
                storage_key="",
                size_bytes=0,  # unknown until upstream is HEAD-probed
                mime_type=mime_type,
                direct_url=url,
            )
        result = await self._ytdlp_info_and_url(
            self._watch_url(video_id), media_type=kind
        )
        if not result:
            raise ProviderUnavailableError(
                f"youtube: could not resolve {kind} stream for {video_id}"
            )
        info, url = result
        meta = _to_metadata(video_id, info)
        # Warm both caches: the URL for repeat streams, the
        # metadata so a follow-up get_info skips yt-dlp.
        await self._stream_cache_put(cache_key, url, meta)
        self._cache_put(video_id, meta)
        return StreamSource(
            storage_key="",
            size_bytes=0,  # unknown until upstream is HEAD-probed
            mime_type=mime_type,
            direct_url=url,
        )

    # ── Native failover: player-client rotation ─────────────────────
    # Innertube flags clients independently: when the web client is
    # walled the android retry (inside _run_ytdlp) may still work, and
    # when android hits licence walls tv/web_embedded/mweb often still
    # answer. This rotation is the *breaker-open* path, so it bypasses
    # _run_ytdlp's fast-fail and cookies (a flagged session poisons
    # these clients too); it only ever runs after the primary path
    # failed, keeping egress pressure low.
    _FALLBACK_CLIENTS = (
        "tv", "tv_embedded", "web_music", "android_music", "web_safari",
        "ios", "mweb", "web_embedded", "android_vr", "tv_simply",
    )
    _FALLBACK_FMT = {
        "audio": "bestaudio/best",
        "video": "18/best[height<=?360][ext=mp4]/best[height<=?360]/best",
    }

    async def rotation_stream(
        self, media_id: str, kind: str = "audio"
    ) -> Optional[StreamSource]:
        """Resolve a stream through the fallback client rotation.

        Returns ``None`` when every client fails (caller keeps its
        original 503 semantics). Success warms the stream/metadata
        caches like the primary path so recovered calls are cheap.
        """
        if not self._ytdlp_argv:
            return None
        vid = media_id.split(":", 1)[1] if media_id.startswith("yt:") else media_id
        if not _YOUTUBE_ID_RE.fullmatch(vid):
            return None
        kind = kind if kind in self._FALLBACK_FMT else "audio"
        mime = "video/mp4" if kind == "video" else "audio/mpeg"
        attempts: List[Tuple[str, bool]] = [(c, False) for c in self._FALLBACK_CLIENTS]
        if self.cookies_file:
            # A pass with uploaded cookies last: YouTube treats the cookie
            # jar as human proof and serves these clients a PO token, which
            # is frequently the ONLY thing that survives an IP bot-check.
            attempts.append(("tv", True))
        for client, use_cookies in attempts:
            args = [
                "--dump-json",
                "-f", self._FALLBACK_FMT[kind],
                "--no-warnings",
                "--no-update",
                "--retries", "1",
                "--socket-timeout", "12",
                "--extractor-args", f"youtube:player_client={client}",
                *(_cookies_args(self.cookies_file) if use_cookies else []),
                *_js_runtime_args(),
                *_proxy_args(self.proxy),
                _YOUTUBE_WATCH.format(vid=vid),
            ]
            result = await _ytdlp_once([*self._ytdlp_argv, *args], timeout=15.0)
            if not result.ok or not result.data:
                continue
            try:
                info = json.loads(
                    result.data.decode(errors="ignore").splitlines()[0]
                )
            except Exception:
                continue
            url = info.get("url")
            if not url or not str(url).startswith("http"):
                continue
            logger.info(
                "yt_rotation_hit",
                extra={"client": client, "video": vid, "kind": kind},
            )
            meta = _to_metadata(vid, info)
            self._cache_put(vid, meta)
            await self._stream_cache_put(f"{vid}:{kind}", str(url), meta)
            return StreamSource(
                storage_key="",
                size_bytes=0,
                mime_type=mime,
                direct_url=str(url),
            )
        _log_ytdlp_fail("rotation", vid, "all fallback player clients failed")
        return None

    # ── Discovery: trending feed + playlist contents ────────────────────
    _PLAYLIST_ID_RE = re.compile(r"^(?:PL|RD|OLAK5uy_|UU|FL|LP|U[LU])[A-Za-z0-9_-]{6,}$")

    async def _ytdlp_flat_json(self, target: str, playlist_end: int = 0) -> Optional[dict]:
        if not self._ytdlp_argv:
            return None
        args = [
            "-J",
            "--flat-playlist",
            "--no-warnings",
            "--no-update",
            "--skip-download",
            "--socket-timeout", "20",
            *_cookies_args(self.cookies_file),
            *_js_runtime_args(),
            *_proxy_args(self.proxy),
        ]
        if playlist_end > 0:
            args += ["--playlist-end", str(playlist_end)]
        forced = breaker_is_open()
        if forced:
            args += ["--extractor-args", "youtube:player_client=tv"]
            args = _strip_cookies(args)
        args.append(target)
        result = await _run_ytdlp(*args, timeout=60.0, bypass_breaker=forced)
        if not result.ok or not result.data:
            _log_ytdlp_fail("dump", target, result.stderr)
            return None
        try:
            return json.loads(result.data.decode(errors="ignore"))
        except Exception:
            return None

    @staticmethod
    def _flat_rows(payload: Optional[dict], limit: int) -> List[MediaMetadata]:
        out: List[MediaMetadata] = []
        seen: set = set()
        for obj in (payload or {}).get("entries") or []:
            if not isinstance(obj, dict):
                continue
            vid = str(obj.get("id") or "")
            if not _YOUTUBE_ID_RE.fullmatch(vid) or vid in seen:
                continue
            seen.add(vid)
            out.append(MediaMetadata(
                media_id=vid,
                title=str(obj.get("title") or vid),
                artist=str(obj.get("channel") or obj.get("uploader") or "") or None,
                duration_seconds=_parse_duration_seconds(obj.get("duration")),
                thumbnail_url=_thumbnail(obj) or None,
                mime_type="audio/mpeg",
                provider="yt",
                views=_stat(obj, "view_count"),
            ))
            if len(out) >= limit:
                break
        return out

    async def trending(self, limit: int = 25) -> List[MediaMetadata]:
        payload = await self._ytdlp_flat_json(
            "https://www.youtube.com/feed/trending", playlist_end=limit
        )
        if payload is None:
            return []
        return self._flat_rows(payload, limit)

    async def get_playlist(
        self, playlist_id: str, limit: int = 50
    ) -> Tuple[str, List[MediaMetadata]]:
        pid = (playlist_id or "").strip()
        if not self._PLAYLIST_ID_RE.fullmatch(pid):
            raise MediaNotFoundError(f"youtube: not a playlist id: {playlist_id!r}")
        payload = await self._ytdlp_flat_json(
            f"https://www.youtube.com/playlist?list={pid}", playlist_end=limit
        )
        if payload is None:
            raise ProviderUnavailableError(
                f"youtube: could not read playlist {pid}"
            )
        entries = self._flat_rows(payload, limit)
        if not entries:
            raise MediaNotFoundError(f"youtube: playlist {pid} empty or private")
        title = str(payload.get("title") or f"YouTube playlist {pid}")
        return title, entries

    # ── transcripts (captions via yt-dlp, key-less) ─────────────────
    async def get_transcript(
        self, media_id: str, language: str = "en"
    ) -> dict:
        """Human/auto captions for a video as timed segments + plain text.

        Pulls subtitle tracks with yt-dlp (explicit subs preferred,
        auto-generated as fallback), converts VTT to timed rows, and
        collapse-caches the result. No API key involved.
        """
        raw = str(media_id).strip()
        if raw.startswith("yt:"):
            raw = raw[3:]
        if "watch?v=" in raw:
            raw = raw.split("watch?v=", 1)[1].split("&", 1)[0]
        vid = self.validate_id(raw)
        lang = self._transcript_lang(language)
        cache_key = f"{vid}:{lang}"
        hit = self._transcript_cache.get(cache_key)
        if hit is not None and hit[0] > time.monotonic():
            return hit[1]

        out_dir = tempfile.mkdtemp(prefix="ytsubs-")
        try:
            result = await _run_ytdlp(
                "--skip-download",
                "--no-warnings",
                "--no-update",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                f"{lang},{lang}-orig,{lang}-*",
                "--sub-format",
                "vtt",
                "-o",
                os.path.join(out_dir, "subs.%(ext)s"),
                "--socket-timeout",
                "20",
                self._watch_url(vid),
                timeout=_TRANSCRIPT_TIMEOUT,
            )
            if not result.ok:
                stderr = result.stderr or ""
                _log_ytdlp_fail("transcript", vid, stderr)
                if any(
                    m in stderr
                    for m in ("Video unavailable", "Private video",
                              "not available", "does not exist")
                ):
                    raise MediaNotFoundError(
                        f"youtube: no such video for transcript: {vid}"
                    )
                raise ProviderUnavailableError(
                    f"youtube: transcript fetch failed for {vid}"
                )
            track = self._pick_vtt(out_dir, lang)
            if track is None:
                raise MediaNotFoundError(
                    f"youtube: video {vid} has no captions (asked {lang!r})"
                )
            with open(track, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            track_lang = os.path.basename(track).split(".", 1)[1].rsplit(".", 1)[0]
            payload = {
                "media_id": f"yt:{vid}",
                "language": track_lang,
                "auto_generated": "-orig" in track_lang,
                "segments": parse_vtt(text),
                "source": "youtube-captions",
            }
            payload["plain_text"] = "\n".join(
                s["text"] for s in payload["segments"]
            )
            if not payload["segments"]:
                raise MediaNotFoundError(
                    f"youtube: caption track for {vid} was empty"
                )
            if len(self._transcript_cache) > _TRANSCRIPT_CACHE_MAX:
                self._transcript_cache.clear()
            self._transcript_cache[cache_key] = (
                time.monotonic() + _TRANSCRIPT_TTL, payload
            )
            return payload
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    @staticmethod
    def _transcript_lang(language: str) -> str:
        cleaned = str(language or "en").strip()
        if not _TRANSCRIPT_LANG_RE.fullmatch(cleaned):
            cleaned = "en"
        return cleaned

    @staticmethod
    def _pick_vtt(out_dir: str, wanted: str) -> Optional[str]:
        candidates: List[str] = []
        root = out_dir
        with contextlib.suppress(FileNotFoundError):
            candidates = [
                os.path.join(root, n)
                for n in sorted(os.listdir(root))
                if n.endswith(".vtt")
            ]
        if not candidates:
            return None
        for path in candidates:
            if os.path.basename(path) == f"subs.{wanted}.vtt":
                return path
        for path in candidates:
            if os.path.basename(path).startswith(f"subs.{wanted}"):
                return path
        return candidates[0]
