"""In-process usage telemetry for the public stats page.

Lightweight, dependency-free counters that describe how the service is
being used right now: searches, resolved tracks, streamed bytes,
downloads, per-provider health, latency percentiles, top tracks/queries
and a rolling event feed. State is persisted (throttled) to a small JSON
file so numbers survive restarts, and every operation is safe to call
from the event loop (plain locks, worst-case O(1) work).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

from app.utils.metrics import active_streams as _active_streams_gauge

_PROVIDER_LABELS = {
    "yt": "YouTube",
    "dz": "Datazalidy",
    "am": "Apple Music",
    "sp": "Spotify",
    "mb": "MusicBrainz",
    "resso": "resso",
    "boomplay": "Boomplay",
    "catalog": "iota Cloud",
    "unknown": "unknown",
}

LATENCY_WINDOW = 600
TRACKS_KEEP = 200
QUERIES_KEEP = 60
LISTENER_TTL_SECONDS = 30.0
IP_HISTORY_TTL_SECONDS = 3600.0


def provider_of(media_id: str) -> str:
    prefix = (media_id or ":").split(":", 1)[0]
    return _PROVIDER_LABELS.get(prefix, prefix or "unknown")


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


class Telemetry:
    def __init__(self, persist_path: str | None = None) -> None:
        self._lock = threading.Lock()
        self._path = persist_path or os.environ.get(
            "IOTA_STATS_FILE",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".data", "telemetry.json"),
        )
        self._started_at = time.time()
        self._last_save = 0.0
        self._load()

    # ── persistence ────────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
        totals = data.get("totals") or {}
        self._totals = {
            "searches": int(totals.get("searches", 0)),
            "songs_fetched": int(totals.get("songs_fetched", 0)),
            "streams": int(totals.get("streams", 0)),
            "downloads": int(totals.get("downloads", 0)),
            "bytes_served": int(totals.get("bytes_served", 0)),
            "errors": int(totals.get("errors", 0)),
            "blocked": int(totals.get("blocked", 0)),
        }
        self._latencies: list[float] = [float(x) for x in (data.get("latency") or [])][-LATENCY_WINDOW:]
        self._search_ms_sum = float(data.get("search_ms_sum", 0.0))
        self._search_ms_n = int(data.get("search_ms_n", 0))
        self._unique_ips = int(data.get("unique_ips", 0))
        self._ip_history: dict[str, float] = {
            str(k): float(v) for k, v in (data.get("ip_history") or {}).items()
        }
        self._providers: dict[str, dict] = {}
        for name, raw in (data.get("providers") or {}).items():
            self._providers[str(name)] = {
                "streams": int(raw.get("streams", 0)),
                "downloads": int(raw.get("downloads", 0)),
                "bytes": int(raw.get("bytes", 0)),
                "latency_sum": float(raw.get("latency_sum", 0.0)),
                "latency_n": int(raw.get("latency_n", 0)),
                "errors": int(raw.get("errors", 0)),
                "last_used": float(raw.get("last_used", 0.0)),
            }
        self._tracks: dict[str, dict] = {}
        for mid, raw in (data.get("tracks") or {}).items():
            self._tracks[str(mid)] = {
                "title": str(raw.get("title") or "Unknown"),
                "provider": str(raw.get("provider") or provider_of(mid)),
                "streams": int(raw.get("streams", 0)),
                "downloads": int(raw.get("downloads", 0)),
                "bytes": int(raw.get("bytes", 0)),
                "last_played": float(raw.get("last_played", 0.0)),
            }
        self._queries: dict[str, int] = {
            str(k): int(v) for k, v in (data.get("queries") or {}).items()
        }
        self._events: list[dict] = []

    def _save(self, force: bool = False) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        now = time.time()
        if not force and now - self._last_save < 5:
            return
        self._last_save = now
        tracks = dict(
            sorted(self._tracks.items(), key=lambda kv: kv[1]["streams"], reverse=True)[:TRACKS_KEEP]
        )
        queries = dict(
            sorted(self._queries.items(), key=lambda kv: kv[1], reverse=True)[:QUERIES_KEEP]
        )
        payload = {
            "totals": self._totals,
            "latency": self._latencies[-LATENCY_WINDOW:],
            "search_ms_sum": self._search_ms_sum,
            "search_ms_n": self._search_ms_n,
            "unique_ips": self._unique_ips,
            "ip_history": self._ip_history,
            "providers": self._providers,
            "tracks": tracks,
            "queries": queries,
        }
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(self._path), prefix=".telemetry-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh)
                os.replace(tmp, self._path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except OSError:
            pass

    # ── recording ──────────────────────────────────────────────────────────
    def record_search(self, query: str, elapsed_ms: float, client_ip: str | None = None) -> None:
        q = (query or "").strip()
        with self._lock:
            self._totals["searches"] += 1
            self._search_ms_sum += max(0.0, float(elapsed_ms))
            self._search_ms_n += 1
            if q:
                self._queries[q] = self._queries.get(q, 0) + 1
            self._note_unique_ip(client_ip)
            self._push_event("search", q or "—", elapsed_ms)

    def note_fetch(self, media_id: str, title: str = "", provider: str = "") -> None:
        with self._lock:
            self._totals["songs_fetched"] += 1
            self._track(media_id, title, provider)
            prov = _PROVIDER_LABELS.get(provider or "", "") or provider_of(media_id)
            self._provider(prov)["last_used"] = time.time()
            self._save()

    def record_stream_start(
        self,
        media_id: str,
        title: str = "",
        provider: str = "",
        client_ip: str | None = None,
    ) -> None:
        now = time.time()
        with self._lock:
            prov = _PROVIDER_LABELS.get(provider or "", "") or provider_of(media_id)
            self._totals["streams"] += 1
            self._provider(prov)["streams"] += 1
            self._provider(prov)["last_used"] = now
            existing = self._tracks.get(media_id)
            track = self._track(media_id, title or (existing or {}).get("title", ""), prov)
            track["streams"] += 1
            track["last_played"] = now
            self._note_unique_ip(client_ip, now)
            self._push_event("stream", track["title"], now)
            self._save()

    def record_stream_bytes(
        self, media_id: str, size_bytes: int, provider: str = ""
    ) -> None:
        if size_bytes <= 0:
            return
        with self._lock:
            prov = _PROVIDER_LABELS.get(provider or "", "") or provider_of(media_id)
            self._totals["bytes_served"] += size_bytes
            self._provider(prov)["bytes"] += size_bytes
            self._track(media_id, "", prov)["bytes"] += size_bytes
            self._save()

    def record_download(
        self, media_id: str, title: str = "", provider: str = "", size_bytes: int = 0
    ) -> None:
        now = time.time()
        with self._lock:
            prov = _PROVIDER_LABELS.get(provider or "", "") or provider_of(media_id)
            self._totals["downloads"] += 1
            self._provider(prov)["downloads"] += 1
            self._provider(prov)["last_used"] = now
            track = self._track(media_id, title, prov)
            track["downloads"] += 1
            track["last_played"] = now
            if size_bytes > 0:
                self._totals["bytes_served"] += size_bytes
                self._provider(prov)["bytes"] += size_bytes
                track["bytes"] += size_bytes
            self._push_event("download", track["title"], now)
            self._save()

    def record_latency(self, ms: float, kind: str = "play", provider: str = "") -> None:
        with self._lock:
            value = max(0.0, float(ms))
            self._latencies.append(value)
            del self._latencies[:-LATENCY_WINDOW]
            if provider:
                p = self._provider(_PROVIDER_LABELS.get(provider, provider))
                p["latency_sum"] += value
                p["latency_n"] += 1

    def note_error(self, kind: str = "error", provider: str = "") -> None:
        with self._lock:
            self._totals["errors"] += 1
            if provider:
                self._provider(_PROVIDER_LABELS.get(provider, provider))["errors"] += 1
            self._push_event("error", kind, 0.0)
            self._save()

    def note_blocked(self) -> None:
        with self._lock:
            self._totals["blocked"] += 1

    # ── snapshot ───────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        now = time.time()
        with self._lock:
            listeners = self._count_listeners(now)
            recent = self._count_recent_ips(now)
            latencies = list(self._latencies)
            total_streams = max(1, self._totals["streams"])
            providers = []
            for name in sorted(self._providers, key=lambda k: self._providers[k]["streams"], reverse=True):
                raw = self._providers[name]
                avg = raw["latency_sum"] / raw["latency_n"] if raw["latency_n"] else 0.0
                providers.append({
                    "name": name,
                    "streams": raw["streams"],
                    "downloads": raw["downloads"],
                    "bytes": raw["bytes"],
                    "avg_latency_ms": round(avg, 1),
                    "errors": raw["errors"],
                    "last_used": raw["last_used"],
                    "share": round(raw["streams"] / total_streams * 100, 1),
                })
            tracks = sorted(
                (
                    {
                        "media_id": mid,
                        "title": t["title"],
                        "provider": t["provider"],
                        "streams": t["streams"],
                        "downloads": t["downloads"],
                        "bytes": t["bytes"],
                        "last_played": t["last_played"],
                    }
                    for mid, t in self._tracks.items()
                ),
                key=lambda t: (t["streams"], t["downloads"], t["bytes"]),
                reverse=True,
            )[:12]
            queries = sorted(
                ({"q": q, "count": n} for q, n in self._queries.items() if q),
                key=lambda x: x["count"],
                reverse=True,
            )[:10]
            events = list(self._events)
            try:
                active_now = int(_active_streams_gauge._value.get())
            except Exception:
                active_now = 0
            search_avg = self._search_ms_sum / self._search_ms_n if self._search_ms_n else 0.0
            payload = {
                "server_started_at": self._started_at,
                "uptime_seconds": round(now - self._started_at, 1),
                "totals": dict(self._totals),
                "live": {
                    "active_listeners": listeners,
                    "unique_listeners_1h": recent,
                    "active_streams": active_now,
                    "search_avg_ms": round(search_avg, 1),
                    "searches_total": self._totals["searches"],
                },
                "latency": {
                    "p50_ms": round(_percentile(latencies, 50), 1),
                    "p95_ms": round(_percentile(latencies, 95), 1),
                    "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
                    "samples": len(latencies),
                },
                "providers": providers,
                "tracks": tracks,
                "queries": queries,
                "events": events,
            }
        return payload

    # ── internals ──────────────────────────────────────────────────────────
    def _provider(self, name: str) -> dict:
        raw = self._providers.get(name)
        if raw is None:
            raw = {
                "streams": 0, "downloads": 0, "bytes": 0,
                "latency_sum": 0.0, "latency_n": 0, "errors": 0, "last_used": 0.0,
            }
            self._providers[name] = raw
        return raw

    def _track(self, media_id: str, title: str, provider: str) -> dict:
        raw = self._tracks.get(media_id)
        if raw is None:
            raw = {
                "title": title or "Unknown",
                "provider": provider or provider_of(media_id),
                "streams": 0, "downloads": 0, "bytes": 0, "last_played": 0.0,
            }
            self._tracks[media_id] = raw
        elif title and raw["title"] == "Unknown":
            raw["title"] = title
        return raw

    def _note_unique_ip(self, ip: str | None, now: float | None = None) -> None:
        if not ip or ip == "unknown":
            return
        now = now or time.time()
        if ip not in self._ip_history:
            self._unique_ips += 1
        self._ip_history[ip] = now
        if len(self._ip_history) > 64:
            cutoff = now - IP_HISTORY_TTL_SECONDS
            stale = [k for k, v in self._ip_history.items() if v < cutoff]
            if not stale:
                stale = sorted(self._ip_history, key=self._ip_history.get)[:32]
            for key in stale:
                self._ip_history.pop(key, None)

    def _count_recent_ips(self, now: float, ttl: float = IP_HISTORY_TTL_SECONDS) -> int:
        cutoff = now - ttl
        return sum(1 for v in self._ip_history.values() if v >= cutoff)

    def _count_listeners(self, now: float) -> int:
        return self._count_recent_ips(now, LISTENER_TTL_SECONDS)

    def _push_event(self, kind: str, label: str, meta: str = "") -> None:
        self._events.insert(
            0,
            {
                "kind": kind,
                "label": str(label)[:80],
                "meta": str(meta)[:60],
                "at": time.time(),
            },
        )
        del self._events[:-40]


telemetry = Telemetry()
