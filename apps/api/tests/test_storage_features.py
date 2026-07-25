"""Phase 31a.0 — consensus-free seasonal-surprise proxy (pure math).

Locks the pre-registered proxy definition: current net change minus the
same-calendar-week average over the prior 5 years, abstaining (None) below
3 distinct prior years.
"""
from __future__ import annotations

from datetime import date

import pytest

from apps.api.services.storage_features import delta_vs_seasonal_norm


def _week(year: int, month: int, day: int) -> date:
    return date(year, month, day)


HISTORY_4Y = [
    (_week(2025, 4, 4), 10.0),
    (_week(2024, 4, 5), 12.0),
    (_week(2023, 3, 31), 14.0),
    (_week(2022, 4, 1), 12.0),
]


def test_known_values():
    # norm = (10 + 12 + 14 + 12) / 4 = 12 → 20 - 12 = 8
    result = delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, HISTORY_4Y)
    assert result == pytest.approx(8.0)


def test_thin_history_abstains():
    # Two prior years < MIN_YEARS=3 → honest absence, not a noisy norm.
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, HISTORY_4Y[:2]) is None


def test_missing_inputs_abstain():
    assert delta_vs_seasonal_norm(None, 20.0, HISTORY_4Y) is None
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), None, HISTORY_4Y) is None
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, []) is None


def test_none_rows_in_history_are_skipped():
    history = [*HISTORY_4Y[:2], (None, 9.0), (_week(2023, 3, 31), None)]
    # Only 2 usable prior years remain → abstain.
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, history) is None


def test_same_year_and_stale_years_excluded():
    history = [
        *HISTORY_4Y[:3],
        (_week(2026, 3, 27), 99.0),  # same year — not a "prior year"
        (_week(2019, 4, 5), 99.0),  # beyond the 5-year lookback
    ]
    result = delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, history)
    # norm from the 3 valid years only: (10 + 12 + 14) / 3 = 12
    assert result == pytest.approx(8.0)


def test_one_row_per_prior_year_closest_week_wins():
    history = [
        (_week(2025, 4, 4), 10.0),  # same ISO week as current → distance 0
        (_week(2025, 4, 11), 99.0),  # adjacent week, same year → ignored
        (_week(2024, 4, 5), 12.0),
        (_week(2023, 3, 31), 14.0),
    ]
    result = delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, history)
    assert result == pytest.approx(20.0 - 12.0)


def test_week_tolerance_of_one():
    # Priors land one ISO week off — still matched (calendar jitter).
    history = [
        (_week(2025, 4, 11), 10.0),
        (_week(2024, 4, 12), 12.0),
        (_week(2023, 4, 7), 14.0),
    ]
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, history) is not None
    # Two-plus weeks off → no match → abstain.
    far = [
        (_week(2025, 5, 2), 10.0),
        (_week(2024, 5, 3), 12.0),
        (_week(2023, 4, 28), 14.0),
    ]
    assert delta_vs_seasonal_norm(_week(2026, 4, 3), 20.0, far) is None


def test_year_end_iso_week_wraparound():
    # Week 52/53 boundary: distance must be circular, not |52 - 1| = 51.
    history = [
        (_week(2025, 12, 26), -100.0),
        (_week(2024, 12, 27), -110.0),
        (_week(2023, 12, 29), -120.0),
    ]
    result = delta_vs_seasonal_norm(_week(2027, 1, 1), -90.0, history)
    assert result == pytest.approx(-90.0 - (-110.0))
