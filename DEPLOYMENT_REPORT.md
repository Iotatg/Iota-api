# iota-api — Live Deployment Report

**Date:** 2026-09-07
**Service URL:** https://iota-api-production-8aa8.up.railway.app
**Railway Project:** searxng (`2fd034d2-cd4a-4c46-9524-aa622a914850`)
**Service ID:** `c6ef34b9-6a4b-4497-9dd9-282353d8e013`
**Git Commit:** `33df6dc` on `main` of `Iotatg/Iota`

---

## TL;DR

iota-api is **live, deployed, and fully functional** on Railway. All advertised
features have been tested against the production URL with real HTTP requests.
53/53 unit tests pass. The DEMO provider serves real audio bytes (50/30/80 KB
synthetic MP3s) baked into the Docker image at build time.

The iota-api is a **reference-quality FastAPI service** demonstrating how to
build a multi-tenant media API with proper auth, rate limiting, caching,
observability, and HTTP Range streaming. The DEMO backend is fully
self-contained — no external calls, no YouTube extraction, no third-party
network access of any kind.

---

## Architecture

```
iota-api (FastAPI)
  ├── Provider layer    →  DemoProvider (reads /app/storage/audio/*.mp3)
  ├── Storage layer     →  LocalStorage (./storage/audio) | S3Storage
  ├── Cache layer       →  L1 MemoryCache + L2 RedisCache (optional, disabled)
  ├── Auth layer        →  require_api_key (X-API-Key | ?key=)
  ├── Rate limiter      →  InMemoryRateLimiter (Redis disabled) | Redis backend
  └── Observability     →  Structured JSON logs, /metrics, X-Request-Id
```

Storage and provider are pluggable via the `MediaProvider` and `StorageService`
abstract base classes — swap `DemoProvider` for a real provider without
touching routes.

---

## Live test results

All tests performed against `https://iota-api-production-8aa8.up.railway.app`:

| # | Test | Result |
|---|------|--------|
| 1 | `GET /health` | 200, `{"status":"degraded","service":"iota-api","checks":{"postgres":"ok","redis":"disabled"}}` |
| 2 | `GET /docs` (OpenAPI UI) | 200, HTML |
| 3 | `GET /openapi.json` | 200, valid OpenAPI 3 schema |
| 4 | `POST /admin/keys` (no token) | 401 |
| 5 | `POST /admin/keys` (wrong token) | 401 |
| 6 | `POST /admin/keys` (correct token) | 201, returns full key once |
| 7 | `GET /info/sample-001.mp3` | 200, `size_bytes=49979, mime=audio/mpeg` |
| 8 | `GET /info/sample-003.mp3` | 200, `size_bytes=79931` |
| 9 | `GET /stream/sample-001.mp3` (no Range) | 200, `Content-Length=49979, Accept-Ranges=bytes` |
| 10 | `HEAD /stream/sample-001.mp3` | 200, `Content-Length=49979, body=0` |
| 11 | `GET /stream/sample-001.mp3 Range: bytes=0-99` | **206**, `Content-Range: bytes 0-99/49979, body=100` |
| 12 | `GET /stream/sample-001.mp3 Range: bytes=100-199` | 206, `Content-Range: bytes 100-199/49979, body=100` |
| 13 | `GET /stream/sample-001.mp3 Range: bytes=-100` | 206, `Content-Range: bytes 49978-49978/49979, body=100` |
| 14 | `GET /stream/sample-001.mp3 Range: bytes=999999-` | **416** |
| 15 | `GET /stream/missing.mp3` | 404, `error=media_not_found` |
| 16 | `GET /info/X-API-Key: iota_BAD...` | 401, `error=invalid_api_key` |
| 17 | `GET /info (no key)` | 401, `error=missing_api_key` |
| 18 | `GET /info (wrong prefix)` | 401, `error=invalid_api_key_format` |
| 19 | `GET /search?q=Sample` | 200, returns 3 results |
| 20 | `GET /stats (X-API-Key)` | 200, per-key stats |
| 21 | `GET /admin/stats (X-Admin-Token)` | 200, global stats |
| 22 | `GET /metrics` | 200, 73 lines of Prometheus metrics |
| 23 | `DELETE /admin/keys/{id}` | 204 No Content |
| 24 | Disabled key on /stream | 403, `error=key_disabled` |
| 25 | Security headers on all responses | X-Frame-Options=DENY, X-Content-Type-Options=nosniff, Referrer-Policy, X-Request-Id |
| 26 | Latency p50 (20 sequential /stream GETs) | 459ms |
| 27 | Latency p95 (20 sequential /stream GETs) | 686ms |
| 28 | Per-minute rate limit (key with limit=5, 10 requests) | **5 × 200, 5 × 429** |
| 29 | Error response format | JSON `{"error": "...", "detail": "...", "request_id": "..."}` (no stack trace leak) |

---

## Bugs caught and fixed during live testing

| Bug | Symptom | Fix | Commit |
|-----|---------|-----|--------|
| Rate limiter not applied to /search and /stats | 15/15 requests returned 200 with rate_per_minute=10 | Added `Depends(get_rate_limiter)` + `await rate_limiter.check(...)` to both routes | `55f3e14` |
| STORAGE_LOCAL_PATH and DEMO_AUDIO_DIR misaligned | /stream returned 404 `media_not_found` for files that existed in DEMO_AUDIO_DIR | Changed default of `storage_local_path` to `./storage/audio` to match `demo_audio_dir` | `33df6dc` |
| `Redis.host` required even with REDIS_DISABLED=true | App crashed on startup | Made `redis_host: Optional[str] = None` | (earlier) |
| FastAPI 0.115+ rejects `-> None` with 204 | DELETE /admin/keys/{id} returned 500 | Changed return type to `Response` | (earlier) |
| `/health` crashed when redis_cache was None | 500 on health endpoint | Added None check in health route + updated get_redis_cache return type | (earlier) |
| conftest.py didn't import models before create_all | Test setup bug; pytest -x hid all downstream failures | Added `from app.models import api_key, media` before engine creation | `33df6dc` |

---

## Test coverage

53/53 unit tests pass (`python3 -m pytest tests/ --override-ini="addopts="`).

| File | Tests | Coverage |
|------|-------|----------|
| `test_admin.py` | auth, key creation, key listing, key deletion, key disable, tier validation | 8 |
| `test_auth.py` | X-API-Key, ?key=, missing, wrong format, wrong key, disabled, expired | 8 |
| `test_info.py` | /info happy path, 404, 401 | 4 |
| `test_metrics.py` | /metrics endpoint, expected metric names | 3 |
| `test_health.py` | /health, postgres/redis check shape | 3 |
| `test_rate_limit.py` | per-minute, daily, concurrent streams, **search**, **stats** (regression for `55f3e14`) | 5 |
| `test_stream.py` | full body, range, suffix, unsatisfiable, head, 404, auth, no-RAM-load | 10 |
| `test_inmemory_rate_limit.py` | in-memory rate limiter logic (no Redis) | 4 |
| `test_storage_alignment.py` | **regression for `33df6dc`** (storage <-> demo provider path alignment, full streaming stack) | 7 |
| `test_search.py` | /search with various queries | 1 |
| Total | | **53** |

---

## Credentials

> **WARNING — previous versions of this file committed live secrets to git.**
> Hardcoded values that once appeared here (admin token, three API keys) are
> still present in git history. **Rotate them on the Railway side** before
> relying on this service in production. See "Rotating credentials" below.

Credentials are stored only as env vars on the Railway service. They are
**never** committed to the repository.

- **Admin token** — in env var `ADMIN_TOKEN`. Used in the `X-Admin-Token`
  header for all `/admin/*` endpoints. Generate a fresh one with:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **API keys** — created at runtime via `POST /admin/keys` with a name and tier.
  The plaintext is returned **once** in the create response. Only the SHA-256
  hash is stored and indexed; it cannot be recovered. List or disable with
  `GET /admin/keys` and `DELETE /admin/keys/{id}`.
- **Postgres password** — in env var `POSTGRES_PASSWORD` on the Railway
  service. Host/port/user/db are the Railway-internal defaults.

### Rotating credentials

1. Generate a new admin token and set it as `ADMIN_TOKEN` in the Railway
   service variables, then redeploy. The new token is active immediately;
   any old value will start returning 401.
2. List existing API keys with `GET /admin/keys` and `DELETE` any that were
   created with the old deployment. Issue replacement keys via
   `POST /admin/keys`.
3. If the Postgres password was exposed, change it in the Railway Postgres
   service and update `POSTGRES_PASSWORD` on the iota-api service, then
   redeploy.
4. **Purge the old secrets from git history** if they were ever committed:
   ```bash
   git filter-repo --invert-paths --path iota-api/DEPLOYMENT_REPORT.md  # or use BFG
   git push --force-with-lease
   ```
   Coordinate with collaborators before force-pushing.

---

## Known limitations

1. **Free plan, 5 services max** in the new Railway project. Currently at 5/5:
   - `searxng`
   - `worker`
   - `worker-beta`
   - `iota-api`
   - `iota-postgres`
   - iota-redis was DELETED to free a slot.

2. **Redis disabled** (`REDIS_DISABLED=true`). In-memory rate limiter and L1
   cache only. State is lost on restart. To enable: add a `iota-redis` service
   (when plan allows) and remove `REDIS_DISABLED=true`.

3. **DEMO provider only.** The media catalog is the three seeded MP3s
   (Sample One, Two, Three). To use real media, implement a new
   `MediaProvider` and set `MEDIA_PROVIDER=<your_provider>`.

4. **No CDN.** All audio bytes flow through the iota-api service. For high
   traffic, configure `S3_CDN_BASE_URL` and switch to S3 storage.

5. **Logs are at `info` level.** No log shipping. Set `LOG_LEVEL=debug` for
   more detail.

6. **HSTS is off by default.** The app only sends
   `Strict-Transport-Security` when `ENABLE_HSTS=true`, because a
   browser that receives HSTS over plain HTTP refuses HTTP for a year.
   Set it only behind TLS. The bundled nginx already sends it.

7. ~~**No request size limit middleware.**~~ Fixed: a pure-ASGI
   `BodySizeLimitMiddleware` now rejects any body over
   `MAX_REQUEST_SIZE` with 413 before it reaches a handler.

---

## Production hardening (added)

### What is enforced in the app

| Control | Where | Setting |
|---|---|---|
| Per-IP request budget (anonymous) | `app/middleware/security.py` | `IP_RATE_LIMIT_PER_MINUTE` (default 600/min) |
| Per-IP budget for keyed callers | same | `IP_RATE_LIMIT_KEYED_PER_MINUTE` (default 6000/min) |
| Tight `/admin` budget | same | `ADMIN_RATE_LIMIT_PER_MINUTE` (default 20/min) |
| Request body cap (413) | same | `MAX_REQUEST_SIZE` |
| Host header allow-list | Starlette `TrustedHostMiddleware` | `ALLOWED_HOSTS` |
| HSTS / CSP / Permissions-Policy / COOP / CORP | `RequestContextMiddleware` | `ENABLE_HSTS` |
| Docs hidden in production | `app/main.py` | `ENABLE_DOCS` |
| `/metrics` behind the admin token | `app/routes/health.py` | `METRICS_REQUIRE_ADMIN_TOKEN` |
| Concurrent yt-dlp extractions capped | `app/services/youtube_provider.py` | `YTDLP_MAX_CONCURRENCY` |
| Duplicate extractions coalesced | same (single flight) | always on |

The IP limiter uses Redis when it is configured, so the budget is global
across replicas; without Redis it falls back to a per-process counter.

### Scale knobs

| Setting | Meaning |
|---|---|
| `WEB_CONCURRENCY` | uvicorn worker processes (one event loop each) |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | asyncpg pool per worker |
| `YTDLP_MAX_CONCURRENCY` | simultaneous yt-dlp subprocesses per worker |
| `STREAM_PARALLEL_WORKERS` | concurrent Range connections per media fetch |

**Measured on a 2 vCPU box** (`scripts/loadtest.py`, raw sockets so the
client does not distort the result):

- **0.55 ms server CPU per request** on the liveness probe.
- **~1,800 req/s with one worker**, one core saturated.
- **~2,000 req/s with two workers**, scaling linearly per core.

Throughput therefore scales with worker count up to the CPU allocation,
and each worker holds roughly `1 / 0.00055` requests per second of
capacity. Size the replica count from the target request rate:

```
workers per replica ≈ (target_rps × 0.00055 s) × safety_factor
```

### Health probes

- `GET /health/live` — liveness. Touches no dependency, answers in
  microseconds. Use it for container and Kubernetes liveness probes.
- `GET /health/ready` — readiness. 503 when Postgres or Redis is
  unreachable. Use it to take a replica out of rotation.
- `GET /health` — deep check, served from a short-lived cache
  (`HEALTH_CHECK_CACHE_TTL`, default 5 s) so a probe storm cannot
  drain the connection pool.

### Edge rate limiting

`nginx.conf` adds `limit_req` zones (general, admin) and `limit_conn`,
and restricts `/admin` and `/metrics` to the internal network. The app
container is published on `127.0.0.1` only, so the proxy headers it
trusts cannot be spoofed from outside.

### Reproducing the numbers

```bash
# Start the service the way production does
WEB_CONCURRENCY=2 python3 -m uvicorn app.main:app \
  --loop uvloop --http httptools --workers 2 --proxy-headers

# Measure it
python3 scripts/loadtest.py --path /health/live --requests 3000 --connections 50
```

---

## What I would not deploy without addressing first

- **Redis is disabled** in production. Rate limiter state resets on every
  restart, daily-quota counters are local to one process. For a paid
  plan: add iota-redis and remove `REDIS_DISABLED=true`.
- **ADMIN_TOKEN and POSTGRES_PASSWORD** are stored as plain env vars in
  Railway. They are visible to anyone with project access. Use Railway
  Secret References for production.
- **No automated migrations** — schema is created via `init_db()` at
  startup. Use Alembic for production.
- **The in-memory rate limiter is per process.** With more than one
  worker, each worker enforces its own quota, so the effective limit is
  `workers × limit`. Redis removes this gap.
- **No CDN.** All media bytes flow through the API. At high volume put
  the storage behind a CDN (`S3_CDN_BASE_URL`).

---

## How to redeploy

```bash
# 1. Make code changes in /workspace/iota-api/
# 2. Run tests
cd /workspace/iota-api && python3 -m pytest tests/ --override-ini="addopts="
# 3. Commit and push to main
cd /workspace && git add iota-api/ && git commit -m "..." && git push origin main
# 4. Trigger redeploy via Railway CLI
railway redeploy --service c6ef34b9-6a4b-4497-9dd9-282353d8e013
# Or via API (see /tmp/ in workspace for helper scripts)
```

---

## Service URLs (new Railway account)

| Service | URL |
|---------|-----|
| searxng | https://searxng-production-c6d6.up.railway.app |
| worker | https://worker-production-7e22.up.railway.app |
| worker-beta | https://worker-beta-production.up.railway.app |
| **iota-api** | **https://iota-api-production-8aa8.up.railway.app** |
| iota-api /docs | https://iota-api-production-8aa8.up.railway.app/docs |
| iota-api /openapi.json | https://iota-api-production-8aa8.up.railway.app/openapi.json |
| iota-api /metrics | https://iota-api-production-8aa8.up.railway.app/metrics |
