# iota-api

Self-hosted music metadata + streaming API built with FastAPI, PostgreSQL, Redis, and pluggable storage backends (local FS or S3-compatible).

> **What this is**: A production-ready reference implementation of a music streaming API with API-key auth, per-minute and daily rate limits, concurrent stream limits, multi-level caching, HTTP Range support, and Prometheus metrics.
>
> **What this is NOT**: A YouTube extractor, a media scraper, or a third-party proxy. The included `DemoProvider` serves local audio files you place in `storage/audio/`. Real providers can be plugged in by subclassing `MediaProvider`.

---

## 1. Features

- **API-key authentication** with `iota_<hex>` format, SHA-256 hashed at rest, never logged.
- **Three-tier rate limiting**: per-minute sliding window, daily quota, concurrent stream slots — all backed by Redis.
- **Multi-level caching**: L1 in-process LRU (per-worker), L2 Redis, L3 object storage.
- **HTTP streaming** with `Range`/`If-Range` support, 206 Partial Content, `Content-Range`, `Accept-Ranges: bytes`. Full file is never loaded into memory.
- **HEAD** requests return headers only (no body) for clients that probe before downloading.
- **Pluggable `MediaProvider`** interface. The shipped `DemoProvider` is a safe default that serves local audio files.
- **Pluggable storage**: local FS (dev) or S3-compatible (prod) — same interface.
- **Admin API** for key management: create, list, get, delete, plus global stats.
- **Prometheus metrics**: `api_requests_total`, `api_request_duration_seconds`, `stream_bytes_total`, `active_streams`, `cache_hits_total`, `cache_misses_total`, `provider_errors_total`.
- **Structured JSON logging** with automatic secret redaction (API keys, admin tokens, signed URLs, cookies, passwords).
- **Security headers** on every response, CORS, request IDs, request timing.
- **Containerized**: `docker-compose.yml` brings up Postgres, Redis, the API, and Nginx in one command.

---

## 2. Architecture

```
                   ┌──────────┐
   ┌──────────────▶│ /admin/* │ (X-Admin-Token, internal only)
   │               └──────────┘
   │
HTTP / nginx :80  ┌──────────┐
──────────────────▶│  iota-api │ :8000
                  │          │
   clients ──────▶│ FastAPI  │── asyncpg ──▶ PostgreSQL :5432
   (X-API-Key)    │  app     │── redis ───▶ Redis      :6379
                  │          │── aiofiles ─▶ Local FS   (./storage)
                  │          │  or boto3 ──▶ S3 / CDN
                  └──────────┘
                       │
                       ▼
                  DemoProvider
                  (./storage/audio/*.mp3)
```

Three layers of cache:

- **L1**: in-process LRU on each API worker. Sub-millisecond. Per-worker state.
- **L2**: Redis, JSON-serialised, with TTL. Shared across workers.
- **L3**: object storage (local FS or S3). The actual audio bytes. Only storage layer that holds the raw data.

Request flow for `GET /stream/{id}`:

1. Authenticate API key (hash lookup in Postgres).
2. Check rate limits (Redis: per-minute, daily, concurrent streams).
3. Resolve media_id via `MediaProvider` (DemoProvider or your custom one).
4. Look up the audio bytes in storage; obtain size.
5. Parse `Range` header → 200 with full body or 206 with `Content-Range`.
6. Stream from storage in chunks (default 64 KiB), wrapped in a `StreamingResponse`. Never full-file in RAM.
7. Update usage counters (Postgres), release concurrent-stream slot, increment Prometheus metrics.

---

## 3. Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET    | `/`              | none  | Service identity |
| GET    | `/health`        | none  | Deep health check (Postgres, Redis) |
| GET    | `/metrics`       | none  | Prometheus exposition |
| GET    | `/search?q=&limit=` | `key` or `X-API-Key` | Search media |
| GET    | `/info/{media_id}` | `key` or `X-API-Key` | Metadata for a media_id |
| GET    | `/stream/{media_id}` | `key` or `X-API-Key` | Stream audio (Range supported) |
| HEAD   | `/stream/{media_id}` | `key` or `X-API-Key` | Headers only |
| GET    | `/stats`         | `key` or `X-API-Key` | Per-key usage stats |
| GET    | `/stream-info/{media_id}` | `key` or `X-API-Key` | Info + a stream URL |
| GET    | `/suggest?q=&limit=` | `key` or `X-API-Key` | YouTube autocomplete (Google completions endpoint) |
| GET    | `/trending?limit=` | `key` or `X-API-Key` | YouTube trending feed (flat extraction; `[]` while bot-blocked) |
| GET    | `/playlists/{playlist_id}?limit=` | `key` or `X-API-Key` | YT playlist contents incl. views (id/URL; `dz:` or Deezer URL → Deezer playlist) |
| GET    | `/lyrics/{media_id}` | `key` or `X-API-Key` | Lyrics (lrclib, lyrics.ovh fallback) |
| GET    | `/similar/{media_id}` | `key` or `X-API-Key` | Related tracks (iTunes/Deezer) |
| GET    | `/charts?kind=&limit=` | `key` or `X-API-Key` | Live chart: tracks/albums/artists/playlists |
| GET    | `/radios?limit=` | `key` or `X-API-Key` | Curated radio stations |
| GET    | `/radios/{radio_id}?limit=` | `key` or `X-API-Key` | Station seed tracks (autoplay filler) |
| GET    | `/genres` | `key` or `X-API-Key` | Full genre tree |
| GET    | `/artists/{name}?limit=` | `key` or `X-API-Key` | Artist profile, discography, top + similar |
| GET    | `/albums/{album_id}?limit=` | `key` or `X-API-Key` | Album with full tracklist |
| GET    | `/entity?kind=&q=&limit=` | `key` or `X-API-Key` | Search playlists/albums/artists/radios |
| GET    | `/transcript/{media_id}?lang=` | `key` or `X-API-Key` | YouTube captions: timed segments + text |

`/search` and `/info` results include `views` (and `likes` where known),
populated natively from YouTube.
| POST   | `/admin/keys`    | `X-Admin-Token` | Create a new API key (returns plaintext ONCE) |
| GET    | `/admin/keys`    | `X-Admin-Token` | List keys (no plaintext) |
| GET    | `/admin/keys/{id}` | `X-Admin-Token` | Single key (no plaintext) |
| DELETE | `/admin/keys/{id}` | `X-Admin-Token` | Disable a key |
| GET    | `/admin/stats`   | `X-Admin-Token` | System-wide stats |

All errors are JSON: `{"error": "<code>", "detail": "<message>", "request_id": "..."}`.

---

## 4. Quick start (Docker)

```bash
# 1. Copy the env template and edit secrets
cp .env.example .env
# At minimum, set POSTGRES_PASSWORD and ADMIN_TOKEN to long random strings.

# 2. Generate a secure ADMIN_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Paste the output into ADMIN_TOKEN= in .env

# 3. Drop a few audio files into storage/audio/ (see Section 8)

# 4. Bring up the stack
docker compose up -d

# 5. Check it's running
curl -s http://localhost/health | jq

# 6. Create an API key
curl -s -X POST http://localhost/admin/keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}' | jq
# Save the value of .api_key — it's only shown once.

# 7. Use the key
KEY="iota_..."
curl -s "http://localhost/info/sample-001.mp3?key=$KEY" | jq
curl -s -i "http://localhost/stream/sample-001.mp3?key=$KEY" -o /dev/null
```

---

## 5. Quick start (local Python)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set up env (use the in-memory equivalents or run Postgres/Redis separately)
cp .env.example .env
# ... edit ...

# Set up a few sample audio files (Section 8)
mkdir -p storage/audio
# ... drop files in ...

# Run
uvicorn app.main:app --reload --port 8000
```

The `--reload` flag is for development only; in production use a process manager (gunicorn / systemd / Docker) and disable reload.

---

## 6. Configuration

All config is via environment variables. See `.env.example` for the full list. Required:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`
- `ADMIN_TOKEN` — at least 32 chars; placeholder values are rejected at startup

Optional with sensible defaults:

- `STORAGE_BACKEND=local` (or `s3`)
- `STREAM_CHUNK_SIZE=65536` (64 KiB)
- `METADATA_CACHE_TTL=300` (5 minutes)
- `API_KEY_PREFIX=iota_`
- `API_KEY_BYTES=32` (32 random bytes = 64 hex chars after the prefix)
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `CORS_ALLOW_ORIGINS=*`

When `STORAGE_BACKEND=s3`, also set: `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and optionally `S3_ENDPOINT` (for R2/MinIO) and `S3_CDN_BASE_URL` (for serving via a CDN instead of signed URLs).

---

## 7. Authentication model

### API key format

```
iota_<64 hex chars>
```

Total: 69 characters, 256 bits of entropy. Format is enforced at creation time. The plaintext is hashed (SHA-256) and only the hash is stored. The plaintext is shown to the caller exactly once at creation and is unrecoverable.

```bash
# Generate a key via the admin API
curl -X POST http://localhost/admin/keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "web-player", "tier": "pro", "daily_limit": 50000}'

# Response (api_key is the plaintext; save it!)
{
  "id": 1,
  "name": "web-player",
  "tier": "pro",
  "daily_limit": 50000,
  "rate_per_minute": 120,
  "concurrent_streams_limit": 5,
  "api_key": "iota_a1b2c3...",
  ...
}
```

Use the key in either of two equivalent ways:

```bash
# Query parameter
curl "http://localhost/info/foo?key=iota_a1b2c3..."

# Or header
curl http://localhost/info/foo -H "X-API-Key: iota_a1b2c3..."
```

### Rate limits

Three independent limits, all per-key, all stored in Redis:

| Limit | Default | Header on 429 |
|-------|---------|---------------|
| Per-minute sliding window | 120 req/min | `Retry-After`, `X-RateLimit-Remaining-Minute` |
| Daily UTC quota | 10,000 req/day | `Retry-After` (seconds until UTC midnight) |
| Concurrent streams | 5 | (no header) |

When a limit is hit, the response is `429 Too Many Requests` with the structured error JSON and the appropriate headers. If Redis is unreachable, the limiter fails CLOSED (returns 503) to prevent abuse during outages.

### Admin token

Single env var, `ADMIN_TOKEN`. Used for all `/admin/*` routes via the `X-Admin-Token` header. Comparison is constant-time. The token is never logged. In production, restrict `/admin/*` to an internal network (see `nginx.conf`).

### Sandbox key (public demo)

The `/api/v1/db/*` routes are document storage and always need a key, there is no anonymous fallback. For the public demo a throwaway sandbox key can be minted without an admin token:

```bash
# Mint a sandbox key
curl -X POST http://localhost/api/v1/keys/anonymous

# Use it
curl http://localhost/api/v1/db/documents \
  -H "X-API-Key: iota_..."
```

Sandbox keys are rate limited like any other key and their documents are removed with the sandbox.

The sandbox key belongs to the document store only. The media endpoints (`/search`, `/info`, `/stream`) read the `api_keys` table, so they need a key that was created through the admin API.

### Media mirror (opt-in)

`IOTA_MIRROR=1` uploads every already delivered YouTube track to the litterbox file host and serves later requests from that mirror. It is off by default because it ships user traffic to a third-party host.

---

## 8. Demo provider and storage

The shipped `DemoProvider` is the reference implementation. It maps `media_id` → file in `storage/audio/`.

```
storage/audio/
├── manifest.json
├── sample-001.mp3
├── sample-002.mp3
└── sample-003.mp3
```

`manifest.json` is optional. If present, it provides title / artist / duration overrides:

```json
{
  "sample-001.mp3": {
    "title": "My First Track",
    "artist": "Me",
    "duration_seconds": 187,
    "mime_type": "audio/mpeg"
  }
}
```

Files without an entry in the manifest use their filename as the title.

**Important**: the demo provider only ever reads from `storage/audio/`. It never reaches the public internet. It is safe to ship in production as a reference; replace it with a real provider by subclassing `MediaProvider` and wiring it in `app/main.py`.

### Seeding the demo directory

```bash
# Drop files in directly
cp ~/Music/track-*.mp3 storage/audio/

# Or use a script
python scripts/seed_demo.py /path/to/music
```

---

## 9. Streaming and Range requests

Every `/stream/{id}` response includes:

```
Accept-Ranges: bytes
Content-Type: audio/mpeg
Content-Length: <bytes>
```

If the request has a `Range: bytes=A-B` header, the response is `206 Partial Content` with:

```
Content-Range: bytes A-B/<total size>
Content-Length: <B - A + 1>
```

Supported range forms:

- `bytes=0-1023` — first 1024 bytes
- `bytes=1024-` — from byte 1024 to end
- `bytes=-512` — last 512 bytes (suffix range)
- `bytes=0-0,-1` — multi-range is NOT supported (returns the first range only, per RFC 9110)

Unsatisfiable ranges (e.g. `bytes=99999-` when the file is 4608 bytes) return `416 Range Not Satisfiable` with no body.

### Performance source — honest notes

The streaming throughput is bounded by:

1. **Disk read speed** of the storage backend (NVMe SSD: ~3 GB/s sequential; HDD: ~150 MB/s; S3 over HTTPS: ~50-200 MB/s depending on object size and region).
2. **Network** between the API and the client.
3. **Single-worker Uvicorn**: only one request can be in-flight on a given worker at a time. With `--workers N`, you get N concurrent streams.
4. **`STREAM_CHUNK_SIZE`**: we read `STREAM_CHUNK_SIZE` bytes at a time from storage and yield each chunk. Larger chunks reduce syscalls; smaller chunks reduce memory. The default (64 KiB) is a good general-purpose setting.

For a 4 KiB MP3 served from local SSD on a single worker, end-to-end TTFB is typically <5 ms. We do not advertise any specific Mbps because it varies wildly with object size, storage backend, network conditions, and worker count. Honest measurement: see your own `/metrics`.

### Memory safety

The full file is NEVER loaded into RAM. The `StreamingResponse` reads `STREAM_CHUNK_SIZE` bytes at a time, yields each chunk to the wire, then reads the next. Even a 10 GB audio file uses ~`STREAM_CHUNK_SIZE` bytes of process memory.

---

## 10. Caching

```
                    ┌────────────────┐
                    │ /info/{id}     │  ← client request
                    └───────┬────────┘
                            │
                  ┌─────────▼─────────┐
                  │  L1 (in-process)  │  Hit?  → return
                  │  MemoryCache      │
                  └─────────┬─────────┘
                            │ Miss
                  ┌─────────▼─────────┐
                  │  L2 (Redis)       │  Hit?  → backfill L1, return
                  │  JSON-serialised  │
                  └─────────┬─────────┘
                            │ Miss
                  ┌─────────▼─────────┐
                  │  Provider         │  → cache.set in L2 (canonical)
                  │  DemoProvider or  │  → L1 backfilled on next read
                  │  your subclass    │
                  └──────────────────┘
```

- L1 TTL is short (≤60s) so per-worker state stays small and stale data is corrected quickly.
- L2 TTL is the user-configured `METADATA_CACHE_TTL` (default 5 min).
- Cache misses are NOT a problem; the provider is fast for the demo and should be fast for any real provider too.

---

## 11. Security

- **API keys**: SHA-256 hashed at rest, never logged, never returned by list/get endpoints. Only the create endpoint returns the plaintext, and only once.
- **Admin token**: never logged, never returned. Constant-time comparison.
- **Structured logging**: every record is single-line JSON. A redaction pass scrubs `api_key`, `authorization`, `cookie`, `password`, `secret`, `token`, signed URL patterns, and `iota_<hex>` patterns from every log message and every field value.
- **Error responses**: structured `{"error", "detail", "request_id"}` — no stack traces, no internal paths, no secrets.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` (no geolocation / camera / mic).
- **CORS**: configurable, defaults to `*`. Lock down in production.
- **Path traversal**: storage keys are resolved under a fixed base directory; out-of-base paths are rejected.
- **SSRF protection**: the demo provider only reads from a local directory. Real providers MUST NOT accept user-supplied URLs.
- **No shell execution**: we never call `os.system`, `subprocess`, or `shell=True`. The codebase has no shell-out paths.
- **Max request size**: enforced by `MAX_REQUEST_SIZE` (1 MiB default) and by Nginx's `client_max_body_size`.
- **Rate limit fail-closed**: if Redis is unreachable, the rate limiter rejects the request (returns 503) rather than allowing unlimited abuse.

---

## 12. Production deployment

For production, at minimum:

1. **Set `APP_ENV=production`** to enable stricter defaults.
2. **Set `ADMIN_TOKEN`** to a 48+ char random string. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
3. **Set `POSTGRES_PASSWORD`** to a strong random password.
4. **Use S3 storage** by setting `STORAGE_BACKEND=s3` and providing bucket + credentials. Use a CDN if you have one.
5. **Put Nginx in front** with TLS. Enable HSTS, gzip, and security headers. (See `nginx.conf` for a starting point.)
6. **Restrict `/admin/*` and `/metrics`** to your internal network (IP allowlist in Nginx, or move them to a separate internal port).
7. **Run multiple Uvicorn workers** (`--workers N`) or use `gunicorn -k uvicorn.workers.UvicornWorker`. Each worker has its own L1 cache; this is fine because L2 (Redis) is the canonical cache.
8. **Set up log aggregation**. The structured JSON logs are designed to be ingested by anything that understands JSON: Loki, Elasticsearch, Splunk, Datadog, etc.
9. **Set up Prometheus scraping** of `/metrics`. The included metric names follow Prometheus conventions.
10. **Add Alembic migrations** before relying on `init_db()` in production. The current code uses `init_db()` for simplicity; in a multi-instance production setup you want migrations so schema changes are atomic.

### Scaling

The app is stateless (all state is in Postgres + Redis + storage). Scale horizontally by adding more Uvicorn workers / more containers. No sticky sessions needed.

### Railway (free plan) deployment notes

Verified working recipe (project `iota`, service `iota-api`):

1. **Builder must be NIXPACKS.** New services default to a builder that ignores `nixpacks.toml`; set it via GraphQL `serviceInstanceUpdate` (`input.builder = NIXPACKS`, plus `startCommand`).
2. **`nixpacks.toml` keep nixPkgs slim**: `["python312", "ffmpeg", "nodejs_20", "deno", "curl"]`. Adding `cacert`/`gcc` triggers an nix profile conflict and the build fails.
3. The Nixpacks image puts the venv at `/opt/venv` (not `/code/.venv`); reference it in health checks / shell probes.
4. **CLI auth**: account-scoped UUID tokens only work via `RAILWAY_API_TOKEN` (not `RAILWAY_TOKEN`, which expects project tokens).
5. **Ephemeral storage**: `DATABASE_URL=sqlite+aiosqlite:////tmp/iota.db` — every redeploy/restart wipes API keys. After each deploy, re-mint one:
   ```bash
   curl -X POST "$URL/admin/keys" -H "X-Admin-Token: $ADMIN_TOKEN" \
     -H 'Content-Type: application/json' -d '{"name":"bot"}'
   ```
   (`X-Admin-Token` header, not Bearer.) Then update the consumer's `.env`. Attach a Railway volume if you want keys to survive redeploys.
6. **Region switching and IPv6 egress are not available on the free plan.** `serviceInstanceUpdate` reports success but the instance keeps the same egress datacenter/IP.
7. **YouTube on datacenter IPs**: the web player client is served an attestation wall ("The page needs to be reloaded" / "Sign in to confirm"). The provider automatically retries with `--extractor-args youtube:player_client=android -4` and strips `--cookies` for that retry (cookies make android-client responses worse). That fallback caps quality at 360p muxed until trusted (age-verified) cookies are supplied via `YOUTUBE_COOKIES_CONTENT`. Installing `yt-dlp-ejs` + deno/node runtimes does not lift the block on flagged IPs.

---

## 13. Plugging in a real provider

Subclass `MediaProvider` and wire it in `app/main.py`:

```python
# app/services/your_provider.py
from app.services.media_provider import (
    MediaProvider, MediaMetadata, StreamSource,
    MediaNotFoundError, ProviderUnavailableError,
)

class YourProvider(MediaProvider):
    name = "your-name"

    async def search(self, query: str, limit: int = 20) -> list[MediaMetadata]:
        # Call your (legally-licensed) source
        ...

    async def get_info(self, media_id: str) -> MediaMetadata:
        ...

    async def get_stream(self, media_id: str) -> StreamSource:
        ...
```

```python
# app/main.py (in lifespan)
from app.services.your_provider import YourProvider
app.state.provider = YourProvider(api_key=os.environ["YOUR_API_KEY"])
```

DO NOT add a provider that fetches from a third-party URL with a key you don't own. DO add providers that wrap legitimate, licensed sources (your own catalog, Jamendo, Free Music Archive, etc.).

---

## 14. Testing

```bash
# Install test deps (already in requirements.txt)
pip install -r requirements.txt

# Run
pytest -v

# Run a specific test
pytest tests/test_stream.py -v
```

The test suite is fully self-contained: SQLite for the database, `fakeredis` for Redis, a temp directory for storage, fake audio bytes. No network access required.

Test coverage:

- `test_health.py` — root, /health, /metrics
- `test_api_key.py` — missing, invalid, expired, disabled, valid (query + header)
- `test_rate_limit.py` — per-minute, daily, concurrent
- `test_cache.py` — info miss/hit, 404, search
- `test_stream.py` — full body, range (start-end, open, suffix), 416, HEAD, 404, auth, chunked
- `test_admin.py` — create, list (no plaintext), get, delete, stats
- `test_stats.py` — per-key stats, auth
- `test_security.py` — secret redaction, no stack traces, security headers, request IDs

---

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ADMIN_TOKEN must be set` at startup | placeholder value | Generate a random token (Section 12) |
| `Redis connection refused` | Redis not running or wrong host | `docker compose up redis -d` or check `REDIS_HOST` |
| `404 media_not_found` on `/stream/sample-001.mp3` | file not in `storage/audio/` | Copy the file in and restart the API |
| `429 rate_limited` immediately | `daily_limit` is 1 or `rate_per_minute` is 1 | Use the admin endpoint to create a key with higher limits |
| `416 range_not_satisfiable` | Range start >= file size | Use `bytes=0-` or `bytes=0-<size-1>` |
| `/metrics` empty | No requests have been made yet | Make a request, then re-check |
| Logs are missing fields | Log level too low | Set `LOG_LEVEL=info` or `LOG_LEVEL=debug` |
| Stream is slow | Storage backend is slow, or workers too few | Add workers, switch to S3 + CDN |

---

## 16. Native discovery + failover

Every discovery feature ships inside iota-api; there are no
third-party API accounts or keys involved:

| Feature | Source |
|---------|--------|
| `views`/`likes` in `/search`,`/info` | yt-dlp / Data API |
| `/suggest` autocomplete | Google YouTube completions (key-less) |
| `/trending`, `/playlists/{id}` | yt-dlp flat extraction |
| `/lyrics/{id}` | lrclib, then lyrics.ovh (both key-less public APIs) |
| `/charts`, `/radios`, `/genres`, `/artists`, `/albums`, `/entity`, Deezer playlists | Deezer public JSON API (key-less catalogue metadata only — audio never comes from Deezer) |
| `/transcript/{id}` | yt-dlp caption tracks (explicit subs, auto-captions fallback) |
| `/stream`,`/download` while YouTube bot-blocks our IP | player-client rotation inside `youtube_provider` (tv, tv_embedded, web_embedded, web_safari, mweb, android_vr) |

The rotation is the failover path when the primary client is
bot-blocked: Innertube flags clients independently, so a rotation
client often still answers while the web client is walled.
`YOUTUBE_BREAKER_THRESHOLD` (default 3) and
`YOUTUBE_BREAKER_COOLDOWN_SECONDS` (default 1800) trip a circuit
breaker after repeated IP-level bot checks so the primary path
fast-fails instead of hammering a flagged IP; a success resets it.
A historical audit of (now removed) third-party audio APIs is kept in
[`docs/THIRD_PARTY_APIS.md`](docs/THIRD_PARTY_APIS.md) for reference.

API keys carry **no limits by default** (`0 = unlimited`; still set
per-key values via the admin API when you need them).

---

## Appendix: project layout

```
iota-api/
├── app/
│   ├── main.py              FastAPI app, middleware, lifespan
│   ├── config.py            Pydantic settings, env loading
│   ├── database.py          SQLAlchemy async engine
│   ├── dependencies.py      Shared FastAPI dependencies
│   ├── auth/
│   │   ├── api_key.py       API key validation
│   │   └── admin.py         Admin token validation
│   ├── cache/
│   │   ├── memory_cache.py  L1: in-process LRU
│   │   ├── redis_cache.py   L2: Redis JSON cache
│   │   └── hierarchy.py     L1 + L2 combined
│   ├── models/
│   │   ├── api_key.py       APIKey ORM
│   │   └── media.py         Media ORM
│   ├── routes/
│   │   ├── health.py        /, /health, /metrics
│   │   ├── stream.py        /stream/* (GET, HEAD, Range)
│   │   ├── info.py          /info/*, /stream-info/*
│   │   ├── search.py        /search
│   │   ├── stats.py         /stats
│   │   └── admin.py         /admin/*
│   ├── schemas/             Pydantic request/response models
│   ├── services/
│   │   ├── media_provider.py   Abstract base
│   │   ├── demo_provider.py    Local-file provider
│   │   └── storage.py          Local + S3 storage
│   └── utils/
│       ├── logging.py       JSON logs + redaction
│       ├── metrics.py       Prometheus
│       └── rate_limit.py    Redis-backed rate limiter
├── tests/                   pytest suite (SQLite + fakeredis)
├── storage/audio/           Local storage for DemoProvider
├── scripts/                 Utility scripts
├── Dockerfile
├── docker-compose.yml       api + postgres + redis + nginx
├── nginx.conf
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
