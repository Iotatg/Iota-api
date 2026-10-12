"""Application configuration loaded from environment variables.

All values are validated at startup. The app refuses to start if any required
value is missing or invalid (see Settings.model_validators).
"""
from __future__ import annotations

import secrets
from enum import Enum
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "iota-api"
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = False
    app_base_url: str = "http://localhost:8000"

    # ── Server ────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # ── PostgreSQL ────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "iota_api"
    postgres_user: str = "iota"
    postgres_password: str = "iota"

    # ── Redis ─────────────────────────────────────────────────────────────
    # Optional when REDIS_DISABLED=true (free-tier deploys use in-memory only).
    redis_disabled: bool = False
    redis_host: Optional[str] = None
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # ── Admin auth ────────────────────────────────────────────────────────
    admin_token: str

    # ── API key config ────────────────────────────────────────────────────
    api_key_prefix: str = "iota_"
    api_key_bytes: int = 32
    default_daily_limit: int = 0
    default_rate_per_minute: int = 0
    default_concurrent_streams: int = 0

    # ── Storage ───────────────────────────────────────────────────────────
    storage_backend: StorageBackend = StorageBackend.LOCAL
    # The demo provider's media_id resolves to <filename> inside this
    # directory, so the default matches DEMO_AUDIO_DIR. If you override
    # one, override both.
    storage_local_path: str = "./storage/audio"
    s3_endpoint: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_cdn_base_url: Optional[str] = None

    # ── Caching ───────────────────────────────────────────────────────────
    metadata_cache_ttl: int = 300
    metadata_cache_max_size: int = 10_000
    rate_limit_window_seconds: int = 60

    # ── Streaming ─────────────────────────────────────────────────────────
    stream_chunk_size: int = 65536
    stream_default_quality: int = 128
    # Concurrent Range connections per proxied stream. CDNs such as
    # YouTube's googlevideo throttle a single connection to a few
    # dozen KB/s; several connections lift throughput to MB/s.
    # Set to 1 to disable parallel streaming.
    stream_parallel_workers: int = 4
    # How long a resolved upstream stream URL is reused before
    # re-resolving. YouTube CDN URLs are valid for hours, so a
    # short TTL lets repeat plays of the same song skip the
    # multi-second yt-dlp extraction. Stale URLs are re-resolved
    # automatically on the next request.
    stream_cache_ttl: int = 120
    # How long a resolved stream URL is cached in the
    # persistent database (survives a restart). YouTube
    # CDN URLs are valid for hours, so this can be much
    # longer than the in-memory TTL. Stale URLs are
    # re-resolved automatically (the route HEAD-probes
    # the URL and invalidates on failure).
    stream_cache_persistent_ttl: int = 3600

    # ── Demo provider ─────────────────────────────────────────────────────
    demo_audio_dir: str = "./storage/audio"

    # ── Multi-provider (YouTube / Spotify / JioSaavn / SoundCloud) ────────
    # All optional. Providers self-disable when their required credential
    # is missing; DemoProvider is always available.
    youtube_api_key: Optional[str] = None
    youtube_cookies_file: Optional[str] = None
    youtube_cookies_content: Optional[str] = None
    youtube_proxy: Optional[str] = None
    youtube_ytdlp_path: Optional[str] = None
    # Max video resolution (height in pixels) for DASH video
    # downloads. YouTube serves resolutions above 720p as
    # separate DASH streams (video-only + audio-only), which
    # iota remuxes with ffmpeg. 0 = best available (up to 8K
    # if the uploader provided it); set e.g. 2160 to cap at
    # 4K or 1080 to cap at 1080p. Audio is unaffected (it
    # always uses the best audio stream).
    youtube_video_max_height: int = 0
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    jiosaavn_api_key: Optional[str] = None
    soundcloud_api_key: Optional[str] = None
    # YouTube circuit breaker: after this many consecutive bot-check /
    # 429 failures, YouTube calls fast-fail for the cooldown window so
    # other sources can serve the request instead of hammering a
    # flagged IP (which prolongs the block). 0 disables the breaker.
    youtube_breaker_threshold: int = 3
    youtube_breaker_cooldown_seconds: int = 1800
    # Upstream proxy timeout (seconds) for the StreamProxy.
    stream_proxy_connect_timeout: float = 10.0
    stream_proxy_read_timeout: float = 60.0

    # ── Security ──────────────────────────────────────────────────────────
    cors_allow_origins: str = "*"
    max_request_size: int = 1_048_576

    # ── Derived helpers ───────────────────────────────────────────────────
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    # ── Validators ────────────────────────────────────────────────────────
    @field_validator("admin_token")
    @classmethod
    def _reject_default_admin_token(cls, v: str) -> str:
        """Refuse to start with a placeholder admin token in production."""
        bad_tokens = {
            "change_me",
            "change_me_to_a_secure_random_token_at_least_32_chars",
            "admin",
            "secret",
            "",
        }
        if v.lower() in bad_tokens:
            raise ValueError(
                "ADMIN_TOKEN must be set to a secure random value. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        if len(v) < 32:
            raise ValueError("ADMIN_TOKEN must be at least 32 characters long.")
        return v

    @field_validator("api_key_prefix")
    @classmethod
    def _validate_api_key_prefix(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError("API_KEY_PREFIX must be alphanumeric (underscores allowed).")
        if not v.endswith("_"):
            raise ValueError("API_KEY_PREFIX must end with an underscore (e.g. 'iota_').")
        return v

    @field_validator("stream_chunk_size")
    @classmethod
    def _validate_chunk_size(cls, v: int) -> int:
        if v < 4096 or v > 1_048_576:
            raise ValueError("STREAM_CHUNK_SIZE must be between 4096 and 1048576 bytes.")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings accessor."""
    return Settings()


def generate_api_key(prefix: str, nbytes: int = 32) -> str:
    """Generate a new API key. Format: <prefix><hex>.

    Returns only the plaintext key. The caller is responsible for hashing
    and showing it to the user exactly once.
    """
    raw = secrets.token_hex(nbytes)
    return f"{prefix}{raw}"


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256.

    We use SHA-256 (not bcrypt) because:
    - API keys are 256-bit random; no brute-force risk even with fast hash.
    - SHA-256 is what we use to look up keys, so it must be fast.
    - For password-equivalent credentials, use bcrypt. API keys are not passwords.
    """
    import hashlib
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
