"""Prometheus metrics for iota-api."""
from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# Use a dedicated registry so tests can reset it if needed
REGISTRY = CollectorRegistry(auto_describe=True)

# ── Request metrics ─────────────────────────────────────────────────────────
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests, labelled by endpoint, method, and status.",
    labelnames=("endpoint", "method", "status"),
    registry=REGISTRY,
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds.",
    labelnames=("endpoint", "method"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# ── Streaming metrics ──────────────────────────────────────────────────────
stream_bytes_total = Counter(
    "stream_bytes_total",
    "Total bytes streamed to clients.",
    labelnames=("endpoint",),
    registry=REGISTRY,
)

active_streams = Gauge(
    "active_streams",
    "Number of currently active streaming responses.",
    registry=REGISTRY,
)

# ── Cache metrics ──────────────────────────────────────────────────────────
cache_hits_total = Counter(
    "cache_hits_total",
    "Cache hits, labelled by level (l1, l2, storage).",
    labelnames=("level",),
    registry=REGISTRY,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Cache misses, labelled by level (l1, l2, storage).",
    labelnames=("level",),
    registry=REGISTRY,
)

# ── Provider metrics ───────────────────────────────────────────────────────
provider_errors_total = Counter(
    "provider_errors_total",
    "Errors from upstream media providers.",
    labelnames=("provider", "kind"),
    registry=REGISTRY,
)


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


def sample_sum(name: str) -> float:
    """Sum every sample of a metric, no matter which labels it carries."""
    total = 0.0
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == name:
                total += sample.value
    return total


def cache_hit_rate() -> float:
    """Share of the cache lookups that were answered from the cache."""
    hits = sample_sum("cache_hits_total")
    misses = sample_sum("cache_misses_total")
    total = hits + misses
    if total <= 0:
        return 0.0
    return hits / total


def active_stream_count() -> int:
    """Number of streams that are currently running."""
    return int(sample_sum("active_streams"))
