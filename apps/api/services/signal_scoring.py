"""
Server-side forecast scoring with deadband logic.
Pure function — no DB, no I/O.
"""
from __future__ import annotations

import math
from typing import Any


def score_forecast(
    direction: str,
    horizon: str,
    expected_pct: float | None,
    realized_pct: float | None,
    deadband: float = 0.003,
) -> dict[str, Any]:
    """
    Returns: {
      "outcome": "hit" | "miss" | "indeterminate" | "neutral" | "pending",
      "realized_pct": float | None,
      "delta_from_expected_pct": float | None,  # realized - expected, signed
    }
    """
    # Treat NaN/inf as None
    if realized_pct is not None and (math.isnan(realized_pct) or math.isinf(realized_pct)):
        realized_pct = None

    if realized_pct is None:
        return {
            "outcome": "pending",
            "realized_pct": None,
            "delta_from_expected_pct": None,
        }

    if direction == "neutral":
        return {
            "outcome": "neutral",
            "realized_pct": realized_pct,
            "delta_from_expected_pct": None,
        }

    if abs(realized_pct) <= deadband:
        outcome = "indeterminate"
    elif (direction == "bullish" and realized_pct > 0) or (direction == "bearish" and realized_pct < 0):
        outcome = "hit"
    else:
        outcome = "miss"

    delta: float | None = None
    if expected_pct is not None and not (math.isnan(expected_pct) or math.isinf(expected_pct)):
        delta = realized_pct - expected_pct

    return {
        "outcome": outcome,
        "realized_pct": realized_pct,
        "delta_from_expected_pct": delta,
    }
