"""Phase B4 — minimal Prometheus metrics.

A deliberately small, genuinely-useful set now that the app is multi-tenant — NOT
a full APM/OTel buildout. Exported as Prometheus text at ``GET /v1/metrics``.

A dedicated registry (not the global default) keeps metric registration stable
across test imports and avoids leaking process-global state.
"""
from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by method/route/status.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by method/route.",
    ["method", "route"],
    registry=REGISTRY,
)
SAFETY_VIOLATIONS = Counter(
    "safety_violations_total",
    "LLM outputs blocked by the safety layer after retry.",
    registry=REGISTRY,
)
AUTO_RESOLUTIONS = Counter(
    "auto_resolutions_total",
    "Decisions auto-resolved by the engine, by outcome.",
    ["outcome"],
    registry=REGISTRY,
)
LEDGER_EVENTS = Counter(
    "ledger_events_total",
    "Immutable decision-ledger events appended, by type.",
    ["event_type"],
    registry=REGISTRY,
)


def render() -> bytes:
    """Prometheus exposition text for the ``/v1/metrics`` endpoint."""
    return generate_latest(REGISTRY)


CONTENT_TYPE = CONTENT_TYPE_LATEST
