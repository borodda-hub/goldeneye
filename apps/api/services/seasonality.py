"""Seasonality — align each calendar year's price path on a common Jan→Dec axis.

The signature energy-desk view: overlay N years of the front-month close by
day-of-year so the seasonal shape (e.g. winter strength in natural gas) is
visible at a glance. Pure transform over daily bars; descriptive, not predictive.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _ts(bar: dict[str, Any]) -> datetime:
    ts = bar["ts"]
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def build_seasonality(bars: list[dict[str, Any]], max_years: int = 6) -> dict[str, Any]:
    """Group bars by calendar year → per-year [{md, v}] series + cross-year mean.

    `md` is "MM-DD". The most recent `max_years` years are kept. The `average`
    line is the mean close across years for each calendar day present.
    """
    by_year: dict[int, list[dict[str, Any]]] = {}
    for b in bars:
        dt = _ts(b)
        by_year.setdefault(dt.year, []).append(
            {"md": f"{dt.month:02d}-{dt.day:02d}", "v": float(b["close"])}
        )

    years_sorted = sorted(by_year.keys())[-max_years:]
    years: list[dict[str, Any]] = []
    # Accumulate for the cross-year average.
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for y in years_sorted:
        # De-dup md (keep last close for that day) and sort by calendar day.
        per_md: dict[str, float] = {}
        for p in by_year[y]:
            per_md[p["md"]] = p["v"]
        points = [{"md": md, "v": round(per_md[md], 4)} for md in sorted(per_md)]
        years.append({"year": y, "points": points})
        for md, v in per_md.items():
            sums[md] = sums.get(md, 0.0) + v
            counts[md] = counts.get(md, 0) + 1

    average = [
        {"md": md, "v": round(sums[md] / counts[md], 4)} for md in sorted(sums)
    ]
    return {"years": years, "average": average}
