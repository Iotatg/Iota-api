"""FastAPI app entrypoint.

Wires together:
- structured JSON logging
- CORS
- security headers
- request id / timing middleware
- global exception handlers
- /, /health, /metrics, /stream/*, /info/*, /search, /stats, /admin/*
"""
from __future__ import annotations

import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Optional

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.cache.hierarchy import CacheHierarchy
from app.cache.memory_cache import MemoryCache
from app.cache.redis_cache import RedisCache
from app.config import get_settings
from app.database import close_db, init_db
from pathlib import Path

from app.catalog.index import SongIndex
from fastapi.staticfiles import StaticFiles

from app.routes import admin, agent, catalog, discovery, download, health, info, iotadb, library, live, pages, search, stats, stream
from app.services.apple_music_provider import AppleMusicProvider
from app.services.boomplay_provider import BoomplayProvider
from app.services.demo_provider import DemoProvider
from app.services.deezer_provider import DeezerProvider
from app.services.jiosaavn_provider import JioSaavnProvider
from app.services.musicbrainz_provider import MusicBrainzProvider
from app.services.provider_registry import ProviderRegistry
from app.services.resso_provider import RessoProvider
from app.services.soundcloud_provider import SoundCloudProvider
from app.services.spotify_provider import SpotifyProvider
from app.services.storage import make_storage
from app.services.stream_cache import StreamCacheService
from app.services.stream_proxy import StreamProxy
from app.services.youtube_provider import YouTubeProvider
from app.utils.logging import configure_logging, get_logger
from app.utils.metrics import api_requests_total
from app.utils.rate_limit import RateLimiter

logger = get_logger(__name__)


def _resolve_youtube_cookies_file(settings) -> Optional[str]:
    """Return the YouTube cookies file path for upstream fetches.

    ``YOUTUBE_COOKIES_CONTENT`` (inline cookie text, used on hosts
    like Railway where shipping a file is awkward) is materialized
    to the same temp path the YouTubeProvider writes, so both the
    extractor and the stream proxy read one file per process.
    """
    if settings.youtube_cookies_content:
        path = os.path.join(tempfile.gettempdir(), "iotatg_yt_cookies.txt")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(settings.youtube_cookies_content)
            os.chmod(path, 0o600)
            return path
        except OSError as exc:
            logger.warning("youtube_cookies_content_write_failed", extra={"err": str(exc)})
    return settings.youtube_cookies_file

# Route groups that live under /api/v1 (library, iotadb). A
# /v1/<group>/... request is aliased to /api/v1/<group>/...
# so a single /v1 base reaches everything, OpenAI-style.
_API_V1_GROUPS = frozenset(
    {"library", "db", "network", "storage", "keys", "auth"}
)


class V1AliasMiddleware:
    """Pure-ASGI middleware that aliases ``/v1/...`` onto the
    canonical route so every endpoint is reachable from a single
    ``/v1`` base (OpenAI-style), without breaking the existing
    root paths or the ``/api/v1`` paths.

    - ``/v1/download/{id}``  -> ``/download/{id}``   (root media routes)
    - ``/v1/stream/{id}``    -> ``/stream/{id}``
    - ``/v1/info/{id}``      -> ``/info/{id}``
    - ``/v1/search``         -> ``/search``
    - ``/v1/library/...``    -> ``/api/v1/library/...`` (api groups)
    - ``/v1/db/...``         -> ``/api/v1/db/...``

    Requests that do not start with ``/v1`` pass through
    untouched, so ``/download/...`` and ``/api/v1/...`` keep
    working exactly as before (forgiving if the prefix is
    forgotten)."""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path == "/v1" or path.startswith("/v1/"):
                scope["path"] = self._rewrite(path)
                scope["raw_path"] = scope["path"].encode("latin-1")
        await self.app(scope, receive, send)

    @staticmethod
    def _rewrite(path: str) -> str:
        rest = path[3:]  # strip the leading "/v1"
        segments = [s for s in rest.split("/") if s]
        if len(segments) >= 2 and segments[0] in _API_V1_GROUPS:
            return "/api/v1/" + "/".join(segments)
        if not segments:
            return "/"
        return "/" + "/".join(segments)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("startup_begin", extra={"env": settings.app_env.value})

    # Redis (optional in single-replica free-tier deploys)
    redis_disabled = os.getenv("REDIS_DISABLED", "false").lower() in ("1", "true", "yes")
    redis_client = None
    if not redis_disabled:
        if not settings.redis_host:
            logger.error("redis_host_required_when_redis_enabled", extra={"hint": "set REDIS_DISABLED=true to skip Redis"})
            raise RuntimeError("REDIS_HOST is required when Redis is enabled")
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=False,
        )
        try:
            await redis_client.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_unreachable_at_startup", extra={"err": str(e)})
            # We continue; rate limiter and L2 will fall back to in-memory.
    else:
        logger.info("redis_disabled_inmemory_only")

    # Postgres
    try:
        await init_db()
        logger.info("postgres_initialized")
    except Exception as e:
        logger.error("postgres_init_failed", extra={"err": str(e)})
        raise

    # Storage
    storage = make_storage()

    # Persistent stream-URL cache (SQLite-backed; survives a
    # restart so repeat plays after a reboot skip yt-dlp).
    stream_cache_service = StreamCacheService(
        ttl=float(settings.stream_cache_persistent_ttl or 0)
    )

    # Provider(s) — build the YouTube provider first because the metadata
    # providers (Spotify / JioSaavn / SoundCloud / Deezer / Apple Music /
    # MusicBrainz / Boomplay / Resso) depend on it. Demo is always
    # available; the others self-disable when their credentials or
    # upstream endpoints are missing.
    youtube = YouTubeProvider(
        api_key=settings.youtube_api_key,
        cookies_file=settings.youtube_cookies_file,
        cookies_content=settings.youtube_cookies_content,
        proxy=settings.youtube_proxy,
        ytdlp_path=settings.youtube_ytdlp_path,
        stream_cache=stream_cache_service,
    )
    spotify = SpotifyProvider(
        youtube=youtube,
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
    jiosaavn = JioSaavnProvider(youtube=youtube)
    soundcloud = SoundCloudProvider(youtube=youtube)
    deezer = DeezerProvider(youtube=youtube)
    apple_music = AppleMusicProvider(youtube=youtube)
    musicbrainz = MusicBrainzProvider(youtube=youtube)
    boomplay = BoomplayProvider(youtube=youtube)
    resso = RessoProvider(youtube=youtube)
    demo = DemoProvider(audio_dir=settings.demo_audio_dir)
    provider = ProviderRegistry([
        demo, youtube, spotify, jiosaavn, soundcloud,
        deezer, apple_music, musicbrainz, boomplay, resso,
    ])

    catalog_path = Path(__file__).resolve().parent.parent / "data" / "songs.json"
    song_index = SongIndex.from_json_path(catalog_path)

    # Stream proxy for remote direct_url sources. The upstream (YouTube
    # CDN) can reject session-minted URLs with 403 unless the fetch
    # carries the same cookies yt-dlp used for extraction, so resolve
    # the cookie source once here and hand it to the proxy.
    stream_proxy = StreamProxy(
        cookies_file=_resolve_youtube_cookies_file(settings)
    )

    # Caches
    l1 = MemoryCache(max_size=settings.metadata_cache_max_size,
                     default_ttl=settings.metadata_cache_ttl)
    if redis_client is not None:
        l2 = RedisCache(redis_client, default_ttl=settings.metadata_cache_ttl)
    else:
        l2 = None
    cache = CacheHierarchy(l1=l1, l2=l2, l1_ttl=min(60, settings.metadata_cache_ttl))

    # Rate limiter
    rate_limiter = RateLimiter(redis_client)

    # Attach to state for dependency functions
    app.state.redis = redis_client
    app.state.memory_cache = l1
    app.state.redis_cache = l2
    app.state.cache = cache
    app.state.rate_limiter = rate_limiter
    app.state.storage = storage
    app.state.provider = provider
    app.state.stream_proxy = stream_proxy
    app.state.song_index = song_index

    logger.info("startup_complete")
    try:
        yield
    finally:
        logger.info("shutdown_begin")
    try:
        await close_db()
    except Exception as e:
        logger.error("shutdown_db_error", extra={"err": str(e)})
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception as e:
            logger.error("shutdown_redis_error", extra={"err": str(e)})
    try:
        await stream_proxy.aclose()
    except Exception as e:
        logger.error("shutdown_stream_proxy_error", extra={"err": str(e)})
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="iota-api",
        version="2.0.0",
        description=(
            "Iota Songs catalog plus IotaDB JSON documents and object storage. "
            "Public catalog is indexed in-process. Authenticated providers remain at /search /info /stream. "
            "Every endpoint is also reachable under a single /v1 base (OpenAI-style): "
            "/v1/download/{id}, /v1/stream/{id}, /v1/info/{id}, /v1/search, /v1/library/... "
            "The root (/download, /stream, ...) and /api/v1/... paths keep working too."
        ),
        lifespan=lifespan,
        docs_url="/swagger",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "Accept-Ranges",
            "Content-Range",
            "Content-Length",
            "X-RateLimit-Remaining-Minute",
            "X-RateLimit-Remaining-Day",
            "Retry-After",
        ],
        max_age=600,
    )

    # ── /v1 path alias (OpenAI-style single base) ───────────────
    # Every endpoint is reachable under /v1 in addition to its
    # canonical root or /api/v1 path.
    app.add_middleware(V1AliasMiddleware)

    # ── Middleware: request id, timing, log ───────────────────────────────
    @app.middleware("http")
    async def request_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception("unhandled_error", extra={"request_id": rid, "err": str(e)})
            response = JSONResponse(
                status_code=500,
                content={"error": "internal_error", "detail": "An internal error occurred.",
                         "request_id": rid},
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        song_count = 0
        try:
            song_count = len(getattr(request.app.state, "song_index", []) or [])
        except Exception:
            song_count = 0
        response.headers["X-Request-Id"] = rid
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Response-Time-MS"] = f"{elapsed_ms:.2f}ms"
        response.headers["X-Powered-By"] = "Iota-Music-Engine"
        response.headers["X-API-Version"] = "2.0.0"
        response.headers["X-Total-Songs"] = str(song_count)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")

        # Metrics
        try:
            endpoint = request.scope.get("route").path if request.scope.get("route") else request.url.path  # type: ignore
        except Exception:
            endpoint = request.url.path
        api_requests_total.labels(
            endpoint=endpoint,
            method=request.method,
            status=str(response.status_code),
        ).inc()

        logger.info("request", extra={
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": elapsed_ms,
        })
        return response

    # ── Global exception handler: normalize HTTP errors ───────────────────
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = getattr(request.state, "request_id", None)
        # If detail is already a structured dict, return it as-is.
        if isinstance(exc.detail, dict):
            body = dict(exc.detail)
            body.setdefault("request_id", rid)
        else:
            body = {"error": "http_error", "detail": str(exc.detail), "request_id": rid}
        return JSONResponse(status_code=exc.status_code, content=body,
                            headers=getattr(exc, "headers", None))

    # ── Routes ────────────────────────────────────────────────────────────
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(pages.router, tags=["pages"])
    app.include_router(agent.router, tags=["agent"])
    app.include_router(catalog.router, tags=["catalog"])
    app.include_router(iotadb.router, tags=["iotadb"])
    app.include_router(health.router, tags=["health"])
    app.include_router(stream.router, tags=["stream"])
    app.include_router(live.router, tags=["live"])
    app.include_router(download.router, tags=["download"])
    app.include_router(info.router, tags=["info"])
    app.include_router(search.router, tags=["search"])
    app.include_router(discovery.router, tags=["discovery"])
    app.include_router(library.router, tags=["library"])
    app.include_router(stats.router, tags=["stats"])
    app.include_router(admin.router, tags=["admin"])

    return app


app = create_app()
