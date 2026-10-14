# Third-party music/stream APIs — capability audit (2026-10-08)

Live-audited capability reference for the external APIs our bot can route to.
All findings were produced by calling their **public APIs** with the tokens
provisioned to us; no internal probing.

Key sources of truth: nubcoder root manifest (`GET /` echoes its endpoint map),
error responses that enumerate `required_arguments` / `optional_arguments`.

---

## 1. nubcoder — `https://api.nubcoders.com` (`ytube_api API` v2026.3.12)

Auth: `Authorization: Bearer <token>` (preferred) or `?token=`. Token issued by
their Telegram bot `@ytdlp_nub_bot` via `/start`.
Quota observed: **100,000 req/day**, resets midnight UTC
(`GET /rate-limit-status` shows usage; our key is non-admin).

| Endpoint | Auth | Status | Notes |
|---|---|---|---|
| `GET /search?q=` (query or scrape mode) | bearer/token | **works** | Returns title, `video_id`, `url`, `duration`, `channel`, **views**, `thumbnail`. ~5 results. |
| `GET /suggest?q=` | free | **works** | Autocomplete to YouTube search results. |
| `GET /trending` | works, **empty** | returns `total_results: 0` — their trending scraper appears dead. |
| `GET /stream?q=<video URL or link>` | **works** | `{ stream_url, time_taken }` in 0.23–0.46s. `redirect=true` returns `redirect_url` instead (their documented "pytgcall" instant pattern). |
| `GET /info?q=` | **works** | One call: title, duration, channel_name, views, video_id, thumbnail, `stream_url`, plus 5 `suggested` tracks. Best single-call metadata+stream. |
| `GET /playlist?url=<playlist URL/ID>` | broken | Radio `RD…` IDs return `total_songs: 0`. Regular `PL` IDs were not tested successfully. Treat as not useful. |
| `GET /health` | free | ok |
| `GET /rate-limit-status` | token | usage counters |

### Stream characteristics (`/stream` resolver URLs)

- Served **from their own proxy** (`/stream/resolver/<opaque>`), **not** ip-pinned —
  verified: our box can fetch a resolver URL generated elsewhere. Safe for bot relay.
- **Supports HTTP Range** (verified `Range: bytes=0-2000000` -> `206`, 2,000,001 bytes).
- `mode=video` (default): h264+aac muxed MP4 **640x360** (~200 kbps video),
  same itag-18 tier we get from the android fallback => their resolver egress is
  also android-tier; **no 720p+ exposed today**. Measured ~2.9 MB/s to our box.
- `mode=audio`: resolver returns `403 {"error":"Upstream returned HTTP 403"}` —
  broken at their side today; do not call it, use yuki for clean audio.

### Verdict for integration

- Use **`/info`** as the fast metadata+stream source (metadata even includes views).
- Use **`/search` + `/suggest`** for free discovery (no YouTube contact from us).
- Use **`/stream` (default mode)** as a secondary 360p source / IP-agnostic relay.
- Avoid `/trending`, `/playlist`, `mode=audio` until they fix them.

---

## 2. yuki — `https://music.yukiapi.site`

Auth: `?key=<key>` or (recommended) header `X-API-Key: <key>`.
Caveat: strict auth checks reject requests with extra query params via
query-key mode with `401` — pass params **with header auth**.

| Endpoint | Status | Response |
|---|---|---|
| `GET /` , `GET /health`, `GET /stats` | ok | `{"status":"running"}` (stats identical to health) |
| `GET /search?q=` | **works** | `{query, results:[{id,title,artist,duration,thumbnail}]}` |
| `GET /stream/<videoId>` | **works** | MP3, **complete file**, ~160 kbps VBR-equivalent (205 s => 3.87 MB), served ~8 MB/s to our box. Their re-encode, so playback-safe everywhere including Telegram voice. |
| `GET /stream/<videoId>?format=m4a` | **works, unreliable for video** (below) | audio/mpeg 200 OK, AAC in MP4 "dash" brand, 3.15 MB. So `format=` is accepted with header auth. |
| `?format=<anything>` (webm/flac/ogg/best/original) | **unreliable** | Server streams **muxed MP4 video** (isom/avc1) from a trusted-looking upstream (tier sizes observed: 8.5 MB, 26.6 MB, 72.5 MB => up to ~1080p-class bitrate) BUT responses are **truncated (moov never arrives)** => not usable. Re-probe periodically; if stable, this is our highest-quality third-party video source. |
| `GET /lyrics?title=<song>` | **works** | JSON `{track_name, artist_name, album_name, lyrics}` |
| `/download /music /info /art /v1/* /openapi.json` | 404 | do not exist |
| `https://play.yukiapi.site` | **dead** | previously confirmed; `music.yukiapi.site` is the live host |

### Verdict for integration

- Primary **audio** source for the bot (best quality/stability/speed combo we have).
- **Lyrics** source for `/lyrics`.
- Watch the `format=` video tiers — when truncation is fixed they likely beat our
  own 360p fallback without any YouTube exposure on our side.

---

## 3. Cloudflare-fronted behavior (both providers)

- Both are behind **Cloudflare** (`cf-ray`, `server: cloudflare`). Our range
  requests, redirects and header behavior must respect standard CF semantics
  (they do: 206 works through their proxies).
- Only public CDN-edge responses were observed; nothing beyond normal API usage.

---

## 4. Routing matrix (recommended)

| Need | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| Search / autocomplete | iota `/search`,`/suggest` (yt native / Google) | nubcoder `/search`,`/suggest` relay | iTunes (existing) |
| Track metadata + views | iota `/info` (yt native) | nubcoder `/info` relay | yuki `/search` |
| Audio playback (voice chat) | iota direct (when YouTube reachable) | **yuki `/stream/<id>` (mp3)** | nubcoder `/stream` mode=video |
| Video 360p relay | iota android (muxed) | nubcoder `/stream` (IP-agnostic proxy + Range) | — |
| Lyrics | lrclib | yuki `/lyrics` | — |
| 4K/8K/1080p | **none available today** (YouTube web client is attestation-blocked from cloud egress — see `README.md` section 12 Railway notes) | — | — |

> **Integration note (2026-10-08, revised):** the matrix above was
> briefly implemented as third-party *feature clients*. Those clients
> have been **removed** — every capability is now served natively
> inside iota-api (Google suggest, lrclib + lyrics.ovh, yt-dlp flat
> extraction for trending/playlists, player-client rotation for
> stream failover). This audit is kept purely for historical reference;
> there are **no `nb:`/`yk:` provider prefixes** and no keys to
> configure —
> the upstreams only answer inside iota's own endpoints, as enrichment
> or fail-soft relays. See `README.md` section 16 for env vars and the
> circuit breaker.
