"""Consensus-free EIA storage surprise proxy (Phase 31a.0).

EIA publishes no analyst-survey consensus (that is a Bloomberg/Refinitiv data
point), so the real adapter leaves `surprise_bcf` NULL and the factor
composite's storage leg would otherwise go dead on real data. The standard
consensus-free alternative is the *seasonal surprise*: this week's net change
vs the average net change for the same calendar week over the prior years.

Pure functions only — callers are responsible for feeding history that was
published on or before their as-of instant (rows from strictly earlier years
satisfy this trivially).
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

# Pre-registered defaults (docs/PHASE_31_PLAN.md §31a.0): a 5-year norm,
# requiring at least 3 distinct prior years so a thin history returns None
# (honest absence) instead of a noisy two-sample "norm".
LOOKBACK_YEARS = 5
MIN_YEARS = 3
# Calendar weeks jitter across years (ISO week 52/53, holiday shifts) — match
# a prior-year row when its ISO week is within ±1 of the current week.
_WEEK_TOLERANCE = 1


def _week_distance(week_a: int, week_b: int) -> int:
    """Circular ISO-week distance, tolerant of the 52/53 year-end wrap."""
    diff = abs(week_a - week_b)
    return min(diff, 53 - diff)


def delta_vs_seasonal_norm(
    week_ending: date | None,
    net_change: float | None,
    history: Sequence[tuple[date | None, float | None]],
    *,
    lookback_years: int = LOOKBACK_YEARS,
    min_years: int = MIN_YEARS,
) -> float | None:
    """Current net change minus the same-calendar-week average of prior years.

    `history` is (week_ending, net_change) pairs for rows OTHER than the
    current one; rows from the current row's own year, rows more than
    `lookback_years` back, missing values, and week mismatches are ignored.
    Per prior year, the single closest week match is used (never two adjacent
    weeks from one year). Returns None unless at least `min_years` distinct
    prior years contribute — a thin history yields honest absence, not noise.
    """
    if week_ending is None or net_change is None:
        return None
    current_week = week_ending.isocalendar()[1]

    # year -> (week_distance, net_change): keep the closest match per year.
    best_by_year: dict[int, tuple[int, float]] = {}
    for prior_we, prior_change in history:
        if prior_we is None or prior_change is None:
            continue
        years_back = week_ending.year - prior_we.year
        if years_back < 1 or years_back > lookback_years:
            continue
        distance = _week_distance(prior_we.isocalendar()[1], current_week)
        if distance > _WEEK_TOLERANCE:
            continue
        existing = best_by_year.get(prior_we.year)
        if existing is None or distance < existing[0]:
            best_by_year[prior_we.year] = (distance, float(prior_change))

    if len(best_by_year) < min_years:
        return None
    norm = sum(change for _dist, change in best_by_year.values()) / len(best_by_year)
    return float(net_change) - norm
