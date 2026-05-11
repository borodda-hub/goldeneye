"""
Generates weekly EIA natural gas storage reports.
100 weekly reports ending 2026-05-08 (most recent Thursday before today).

Algorithm (from docs/MOCK_DATA_SPEC.md):
- Annual cycle: trough ~1500 Bcf late March, peak ~3700 Bcf early November
- Seasonal net_change_bcf: computed as derivative of the annual curve + N(0, 12)
- consensus_estimate = actual + N(0, 8) -- i.e., consensus is actual plus analyst error
- surprise_bcf = actual - consensus
- Regional splits: east=18%, midwest=24%, mountain=5%, pacific=7%, south_central=46% (sum=100%)
  Apply small per-region noise so they sum exactly to total
- five_year_avg_bcf: the annual-cycle base without noise
- five_year_max_bcf: avg + 200
- five_year_min_bcf: avg - 200

Return format from generate() -> list[dict]:
  [{"report_date": date, "week_ending": date, "total_lower_48_bcf": float,
    "east_bcf": float, "midwest_bcf": float, "mountain_bcf": float,
    "pacific_bcf": float, "south_central_bcf": float, "net_change_bcf": float,
    "five_year_avg_bcf": float, "five_year_max_bcf": float, "five_year_min_bcf": float,
    "consensus_estimate": float, "surprise_bcf": float, "source": "mock"}, ...]

Dates: report_date is Thursday (published), week_ending is the previous Friday.
Generate 100 reports ending on 2026-05-08 (most recent Thursday).
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Regional allocation weights (must sum to 1.0)
REGION_WEIGHTS = {
    "east": 0.18,
    "midwest": 0.24,
    "mountain": 0.05,
    "pacific": 0.07,
    "south_central": 0.46,
}

# Annual cycle parameters
# Trough ~1500 Bcf at day ~80 (late March), peak ~3700 Bcf at day ~305 (early November)
STORAGE_AMPLITUDE = (3700 - 1500) / 2   # = 1100
STORAGE_MIDPOINT  = (3700 + 1500) / 2   # = 2600
PEAK_DOY = 305  # early November


def _storage_base(report_date: date) -> float:
    """Annual storage cycle baseline value for given date."""
    doy = report_date.timetuple().tm_yday
    angle = 2 * math.pi * (doy - PEAK_DOY) / 365
    return STORAGE_MIDPOINT + STORAGE_AMPLITUDE * math.cos(angle)


def _storage_derivative(report_date: date) -> float:
    """Weekly change implied by the annual cycle (dBase/dWeek)."""
    # Derivative of cosine cycle: -A * sin(angle) * (2π/365) per day * 7 days/week
    doy = report_date.timetuple().tm_yday
    angle = 2 * math.pi * (doy - PEAK_DOY) / 365
    # Rate of change per day
    daily_rate = -STORAGE_AMPLITUDE * math.sin(angle) * (2 * math.pi / 365)
    return daily_rate * 7  # weekly change


def generate() -> list[dict[str, Any]]:
    """Generate 100 weekly EIA storage reports ending 2026-05-08."""
    rng = np.random.default_rng(42)

    # Most recent Thursday on or before 2026-05-10
    end_thursday = date(2026, 5, 7)
    assert end_thursday.weekday() == 3, f"Expected Thursday, got weekday {end_thursday.weekday()}"

    # Build list of 100 Thursdays ending on end_thursday
    report_dates = []
    d = end_thursday
    for _ in range(100):
        report_dates.append(d)
        d -= timedelta(weeks=1)
    report_dates.reverse()  # chronological order

    rows: list[dict[str, Any]] = []

    for report_date in report_dates:
        # week_ending is the previous Friday (6 days before Thursday)
        week_ending = report_date - timedelta(days=6)
        assert week_ending.weekday() == 4, f"week_ending should be Friday, got {week_ending}"

        # Five-year average (no noise)
        five_yr_avg = round(_storage_base(week_ending), 1)
        five_yr_max = round(five_yr_avg + 200, 1)
        five_yr_min = round(five_yr_avg - 200, 1)

        # Net change: seasonal derivative + noise
        seasonal_change = _storage_derivative(week_ending)
        net_change = round(seasonal_change + rng.normal(0, 12), 1)

        # Compute total from running sum — but since we don't track state between calls,
        # derive total from the annual cycle base + accumulated noise
        # Use the base for the week_ending date
        total = round(_storage_base(week_ending) + rng.normal(0, 30), 1)
        total = max(total, 100.0)  # floor

        # Regional splits with noise summing exactly to total
        raw_splits = {
            region: REGION_WEIGHTS[region] * total + rng.normal(0, 2)
            for region in REGION_WEIGHTS
        }
        # Normalize so they sum exactly to total
        raw_sum = sum(raw_splits.values())
        splits = {
            region: round(val / raw_sum * total, 1)
            for region, val in raw_splits.items()
        }
        # Adjust the largest region (south_central) to absorb rounding error
        split_sum = sum(splits.values())
        splits["south_central"] = round(splits["south_central"] + (total - split_sum), 1)

        # Consensus: actual + analyst error  →  consensus = net_change + error
        analyst_error = rng.normal(0, 8)
        consensus_estimate = round(net_change + analyst_error, 1)
        surprise_bcf = round(net_change - consensus_estimate, 1)

        rows.append({
            "report_date": report_date,
            "week_ending": week_ending,
            "total_lower_48_bcf": total,
            "east_bcf": splits["east"],
            "midwest_bcf": splits["midwest"],
            "mountain_bcf": splits["mountain"],
            "pacific_bcf": splits["pacific"],
            "south_central_bcf": splits["south_central"],
            "net_change_bcf": net_change,
            "five_year_avg_bcf": five_yr_avg,
            "five_year_max_bcf": five_yr_max,
            "five_year_min_bcf": five_yr_min,
            "consensus_estimate": consensus_estimate,
            "surprise_bcf": surprise_bcf,
            "source": "mock",
        })

    return rows


if __name__ == "__main__":
    rows = generate()
    print(f"Generated {len(rows)} EIA storage reports")
    print(f"First: {rows[0]}")
    print(f"Last:  {rows[-1]}")
