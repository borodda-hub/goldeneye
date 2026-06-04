"""Fundamentals service — latest weekly inventory/stock data per instrument.

Asset-class aware:
- NG  → EIA natural-gas working-gas-in-storage (rich: net change, surprise, 5-yr).
- CL/HO/RB → EIA petroleum weekly stocks via the per-symbol energy adapter.
- Everything else (metals, grains, …) → honest "no fundamentals" empty state
  (the registry already returns NullEnergyAdapter, so there is no data to show).

Raw factual data — no safety wrapper (that is for model/LLM output only). Each
record carries an `as_of` for freshness labeling.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.energy.eia_petroleum import PETROLEUM_SERIES
from apps.api.adapters.registry import get_energy
from apps.api.repos import eia as eia_repo

_GAS_TITLE, _GAS_UNIT = "Working Gas in Storage", "Bcf"

# Presentation for the petroleum-product / crude paths (CL/HO/RB).
_PETROLEUM_META: dict[str, tuple[str, str]] = {
    "CL": ("Crude Stocks · Cushing", "Mbbl"),
    "HO": ("Distillate Stocks", "Mbbl"),
    "RB": ("Gasoline Stocks", "Mbbl"),
}

_EMPTY_REASON = "No EIA inventory report for this asset class"


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _empty(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "kind": "none",
        "title": "Fundamentals",
        "unit": None,
        "latest": None,
        "source": None,
        "empty_reason": _EMPTY_REASON,
    }


async def get_fundamentals(session: AsyncSession, symbol: str) -> dict[str, Any]:
    up = symbol.upper()

    if up == "NG":
        row = await eia_repo.get_latest(session)
        if row is None:
            return _empty(symbol)
        return {
            "symbol": symbol,
            "kind": "gas_storage",
            "title": _GAS_TITLE,
            "unit": _GAS_UNIT,
            "latest": {
                "as_of": _iso(row.week_ending),
                "level": _f(row.total_lower_48_bcf),
                "net_change": _f(row.net_change_bcf),
                "surprise": _f(row.surprise_bcf),
                "five_year_avg": _f(row.five_year_avg_bcf),
            },
            "source": row.source or "EIA",
            "empty_reason": None,
        }

    if up in PETROLEUM_SERIES:  # CL / HO / RB
        adapter = get_energy(up)
        latest = await adapter.get_latest_storage()
        if not latest:
            return _empty(symbol)
        title, unit = _PETROLEUM_META.get(up, ("Product Stocks", "Mbbl"))
        return {
            "symbol": symbol,
            "kind": "petroleum_stocks",
            "title": title,
            "unit": unit,
            "latest": {
                "as_of": _iso(latest.get("week_ending")),
                "level": _f(latest.get("total_lower_48_bcf")),
                "net_change": _f(latest.get("net_change_bcf")),
                "surprise": _f(latest.get("surprise_bcf")),
                "five_year_avg": None,
            },
            "source": latest.get("source") or "eia_petroleum",
            "empty_reason": None,
        }

    return _empty(symbol)
