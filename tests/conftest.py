"""Pytest configuration and shared fixtures.

Tests run in-process: no real Postgres, no real Redis, no real S3. We use:
- SQLite (via aiosqlite) for the database
- fakeredis for the Redis client
- A temp directory for the local storage backend
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

# Set up environment BEFORE any app import
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "iota_test")
os.environ.setdefault("POSTGRES_USER", "iota")
os.environ.setdefault("POSTGRES_PASSWORD", "iota")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("ADMIN_TOKEN", "test_admin_token_" + "x" * 32)
os.environ.setdefault("API_KEY_PREFIX", "iota_")
os.environ.setdefault("STORAGE_BACKEND", "local")

TEST_ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def temp_audio_dir() -> AsyncIterator[Path]:
    """Create a temp dir with fake audio files and a manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "sample-001.mp3").write_bytes(b"FAKEAUDIO" * 512)  # 4 KiB
        (tmp_path / "sample-002.mp3").write_bytes(b"FAKEAUDIO" * 256)  # 2 KiB
        (tmp_path / "sample-003.mp3").write_bytes(b"FAKEAUDIO" * 1024) # 8 KiB
        (tmp_path / "manifest.json").write_text(
            '{"sample-001.mp3": {"title": "Sample One", "artist": "Test Artist", "duration_seconds": 60},'
            ' "sample-002.mp3": {"title": "Sample Two", "artist": "Other Artist", "duration_seconds": 30},'
            ' "sample-003.mp3": {"title": "Sample Three", "artist": "Test Artist", "duration_seconds": 120}}'
        )
        yield tmp_path


@pytest_asyncio.fixture
async def fake_redis():
    """A fakeredis.aioredis instance (full redis API)."""
    import fakeredis.aioredis as faio
    client = faio.FakeRedis(decode_responses=False)
    yield client
    try:
        await client.aclose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def app_instance(temp_audio_dir, fake_redis, monkeypatch):
    """Build a FastAPI app instance with test doubles for Postgres/Redis."""
    # Patch the database engine to use SQLite before app imports
    monkeypatch.setenv("DEMO_AUDIO_DIR", str(temp_audio_dir))
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(temp_audio_dir))

    # Import models BEFORE creating the engine so they register with Base.metadata
    from app.models import api_key, iotadb, library, media, stream_cache  # noqa: F401

    # Patch the database engine and session factory
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app import database

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    test_session_factory = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, autoflush=False
    )
    database.engine = test_engine
    database.AsyncSessionLocal = test_session_factory

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    # Build app
    from app.cache.hierarchy import CacheHierarchy
    from app.cache.memory_cache import MemoryCache
    from app.cache.redis_cache import RedisCache
    from app.main import create_app
    from app.services.demo_provider import DemoProvider
    from app.services.storage import LocalStorage
    from app.services.stream_proxy import StreamProxy
    from app.catalog.index import SongIndex
    from app.utils.rate_limit import RateLimiter

    app = create_app()

    storage = LocalStorage(base_path=str(temp_audio_dir), public_base_url="http://test")
    provider = DemoProvider(audio_dir=str(temp_audio_dir))
    l1 = MemoryCache(max_size=1000, default_ttl=60)
    l2 = RedisCache(fake_redis, default_ttl=60)
    cache = CacheHierarchy(l1=l1, l2=l2, l1_ttl=30)
    rate_limiter = RateLimiter(fake_redis)
    stream_proxy = StreamProxy()

    app.state.redis = fake_redis
    app.state.memory_cache = l1
    app.state.redis_cache = l2
    app.state.cache = cache
    app.state.rate_limiter = rate_limiter
    app.state.storage = storage
    app.state.provider = provider
    app.state.stream_proxy = stream_proxy
    app.state.song_index = SongIndex(
        [
            {
                "video_id": "iotademo001",
                "title": "Neon Drift",
                "artist": "Iota Ensemble",
                "stream_url": "/api/file/iotademo001",
                "source": "iota_cloud",
                "thumbnail": "/static/thumbs/default.svg",
                "duration_seconds": 180,
                "tags": ["electronic", "demo"],
            },
            {
                "video_id": "iotademo002",
                "title": "Midnight Circuit",
                "artist": "Violet Wave",
                "stream_url": "/api/file/iotademo002",
                "source": "iota_cloud",
                "thumbnail": "/static/thumbs/default.svg",
                "duration_seconds": 210,
                "tags": ["synth", "demo"],
            },
        ]
    )

    yield app

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(app_instance) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def created_key(app_instance) -> dict:
    """Create an API key via the admin endpoint and return the full response."""
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/admin/keys",
            json={"name": "test-key"},
            headers={"X-Admin-Token": TEST_ADMIN_TOKEN},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()


@pytest_asyncio.fixture
async def auth_headers(created_key) -> dict:
    return {"X-API-Key": created_key["api_key"]}
