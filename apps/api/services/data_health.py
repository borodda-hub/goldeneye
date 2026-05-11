"""
Data-health rollup service.

Reads adapter_runs and rolls up per-adapter status using cadence-based rules:
  - ok        — last success within expected cadence × 1.5
  - degraded  — last success within expected cadence × 3 (but past 1.5×)
  - down      — beyond 3× OR last run status was "error"
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# Expected cadence in minutes, per adapter name prefix.
# Lookup is best-match by prefix; unknown adapters default to 60 minutes.
EXPECTED_CADENCE_MIN: dict[str, int] = {
    "market.": 5,
    "energy.eia.storage": 7 * 24 * 60,     # weekly Thursday
    "positioning.cftc.cot": 7 * 24 * 60,   # weekly Friday
    "weather.nws": 6 * 60,                  # 6 hours
    "weather.": 6 * 60,
    "news.": 30,
}
DEFAULT_CADENCE_MIN: int = 60


def expected_cadence_minutes(adapter_name: str) -> int:
    """Return the expected cadence (minutes) for an adapter name."""
    for prefix, mins in EXPECTED_CADENCE_MIN.items():
        if adapter_name.startswith(prefix):
            return mins
    return DEFAULT_CADENCE_MIN


def classify_status(
    adapter_name: str,
    last_finished_at: datetime | None,
    last_status: str | None,
    now: datetime | None = None,
) -> str:
    """
    Classify an adapter's health.

    Args:
      adapter_name: e.g. "energy.eia.storage", "market.mock"
      last_finished_at: timestamp of last completed run; None means never ran.
      last_status: status of the last run ("ok" | "error" | None)
      now: override for "current time" (testing).

    Returns: "ok" | "degraded" | "down"
    """
    if last_status == "error":
        return "down"
    if last_finished_at is None:
        return "down"

    current = now or datetime.utcnow()
    lag_minutes = (current - last_finished_at).total_seconds() / 60.0
    cadence = expected_cadence_minutes(adapter_name)

    if lag_minutes <= cadence * 1.5:
        return "ok"
    if lag_minutes <= cadence * 3.0:
        return "degraded"
    return "down"


def rollup_adapter_run(run: Any, now: datetime | None = None) -> dict[str, Any]:
    """
    Convert a single AdapterRun ORM row into the data-health envelope shape.
    """
    current = now or datetime.utcnow()
    finished_at = getattr(run, "finished_at", None)
    last_status = getattr(run, "status", None)
    name = getattr(run, "adapter_name", "unknown")

    status = classify_status(name, finished_at, last_status, now=current)
    lag_minutes: float | None = None
    if finished_at is not None:
        lag_minutes = round((current - finished_at).total_seconds() / 60.0, 1)

    return {
        "name": name,
        "status": status,
        "last_success": finished_at.isoformat() if finished_at is not None else None,
        "lag_minutes": lag_minutes,
        "rows_ingested": getattr(run, "rows_ingested", None),
        "error": getattr(run, "error", None),
        "expected_cadence_minutes": expected_cadence_minutes(name),
    }
