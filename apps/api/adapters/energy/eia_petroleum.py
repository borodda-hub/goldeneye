"""Real EIA Petroleum adapter — weekly product/stock series per instrument.

Used by the signals path when the active instrument is a petroleum product so
xgboost has alt-data parity with what NG gets from the natural-gas storage
adapter. Phase 17 generalized this from Cushing-crude-only to a per-symbol
series table:

- CL → Cushing OK ending stocks (primary) + total Lower-48 ex-SPR (context)
- HO → total distillate (incl. heating oil/diesel) stocks
- RB → total motor gasoline stocks

Cushing is the canonical delivery point for the NYMEX WTI contract; distillate
and gasoline stocks are the most price-relevant weekly series for HO and RB.

This adapter intentionally does NOT persist into the eia_storage_reports table —
that schema is shaped for natural-gas (BCF columns, regional breakdowns). The
quartet routes alt-data live through this adapter (24h-cached) without DB
persistence; a future phase can add an eia_petroleum_stocks hypertable if
backfilled history becomes useful.

Returns the same dict shape as the natural-gas adapter for the fields the
signals path consumes — `surprise_bcf`, `net_change_bcf`, `actual_bcf`. Values
are in thousand barrels (mbbl); the `_bcf` suffix is retained only for shape
compatibility and the xgboost placeholder is unit-agnostic.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, NamedTuple

from apps.api.adapters._http import AdapterHTTPClient
from apps.api.src.settings import settings

logger = logging.getLogger(__name__)

EIA_BASE_URL = "https://api.eia.gov/v2/"
PETROLEUM_ROUTE = "petroleum/stoc/wstk/data/"


class PetroleumSeries(NamedTuple):
    """EIA weekly-stock series IDs for one instrument.

    `primary` is the price-relevant stock level (deltas are computed off it).
    `context` is an optional broader series kept for shape parity with the
    natural-gas adapter (only CL uses it). Series IDs verified live against
    EIA Open Data v2 — recheck if EIA reissues.
    """

    primary: str
    context: str | None


PETROLEUM_SERIES: dict[str, PetroleumSeries] = {
    "CL": PetroleumSeries(primary="WCESTP31", context="WCESTUS1"),  # Cushing + total ex-SPR
    "HO": PetroleumSeries(primary="WDISTUS1", context=None),        # total distillate stocks
    "RB": PetroleumSeries(primary="WGTSTUS1", context=None),        # total motor gasoline stocks
}

# 24h cache — weekly publication on Wednesdays makes more frequent calls wasteful.
_CACHE_TTL_SECONDS = 24 * 60 * 60


class EIAPetroleumAdapter:
    """Real petroleum-stocks adapter for a single petroleum instrument.

    Conforms to the slice of EnergyDataAdapter that signals.py actually
    consumes: `get_latest_storage()` returning a dict with `surprise_bcf`,
    `net_change_bcf`, and an `actual_*` field. The bcf naming is preserved so
    downstream xgboost code doesn't need conditional branches.
    """

    def __init__(self, symbol: str = "CL") -> None:
        up = symbol.upper() if symbol else "CL"
        if up not in PETROLEUM_SERIES:
            raise ValueError(
                f"No EIA petroleum series registered for symbol {up!r}. "
                f"Known symbols: {sorted(PETROLEUM_SERIES)}"
            )
        self._symbol = up
        self._series = PETROLEUM_SERIES[up]
        self._client = AdapterHTTPClient(
            adapter_name=f"energy.eia.petroleum.{up.lower()}"
        )
        self._cache: tuple[float, list[dict[str, Any]]] | None = None

    async def get_storage_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        reports = await self._get_reports_cached()
        return reports[:limit]

    async def get_latest_storage(self) -> dict[str, Any] | None:
        reports = await self._get_reports_cached()
        return reports[0] if reports else None

    async def _get_reports_cached(self) -> list[dict[str, Any]]:
        now = time.time()
        if self._cache is not None:
            cached_at, cached_data = self._cache
            if now - cached_at < _CACHE_TTL_SECONDS:
                return cached_data
        try:
            raw = await self._fetch()
            reports = _pivot(raw, self._series)
        except Exception as exc:
            logger.warning(
                "EIA petroleum fetch failed for %s: %s — empty result.",
                self._symbol,
                exc,
            )
            reports = []
        self._cache = (now, reports)
        return reports

    async def _fetch(self) -> list[dict[str, Any]]:
        api_key = settings.eia_api_key
        if not api_key:
            return []
        params: list[tuple[str, str]] = [
            ("api_key", api_key),
            ("frequency", "weekly"),
            ("data[]", "value"),
            ("sort[0][column]", "period"),
            ("sort[0][direction]", "desc"),
            ("length", "260"),  # ~5 years weekly
            ("facets[series][]", self._series.primary),
        ]
        if self._series.context is not None:
            params.append(("facets[series][]", self._series.context))
        url = EIA_BASE_URL + PETROLEUM_ROUTE
        response = await self._client.get(url, params=params)
        body = response.json()
        data = body.get("response", {}).get("data", [])
        return data if isinstance(data, list) else []


def _pivot(
    rows: list[dict[str, Any]], series: PetroleumSeries
) -> list[dict[str, Any]]:
    """Pivot per-(period, series) rows into one record per week_ending.

    Output shape matches the natural-gas adapter so signals.py can read
    `surprise_bcf` and `net_change_bcf` without conditional branches. Values
    are in thousand barrels (mbbl); the `_bcf` field names retain that suffix
    only for shape compatibility (the xgboost placeholder is unit-agnostic and
    uses magnitudes relative to themselves).
    """
    primary_id = series.primary
    context_id = series.context
    by_period: dict[str, dict[str, float]] = {}
    for row in rows:
        period = row.get("period")
        s = row.get("series")
        value = row.get("value")
        if period is None or value is None:
            continue
        try:
            fvalue = float(value)
        except (TypeError, ValueError):
            continue
        if s == primary_id:
            by_period.setdefault(period, {})["primary"] = fvalue
        elif context_id is not None and s == context_id:
            by_period.setdefault(period, {})["context"] = fvalue

    records: list[dict[str, Any]] = []
    for period_str in sorted(by_period.keys(), reverse=True):
        try:
            week_ending = date.fromisoformat(period_str)
        except ValueError:
            continue
        fields = by_period[period_str]
        primary = fields.get("primary")
        context = fields.get("context")
        records.append(
            {
                "report_date": week_ending,
                "week_ending": week_ending,
                "total_lower_48_bcf": primary,  # shape compat — primary stock (mbbl)
                "actual_bcf": primary,
                "total_ex_spr_mbbl": context,  # canonical CL-side name; None for HO/RB
                "net_change_bcf": None,
                "consensus_estimate": None,
                "surprise_bcf": None,
                "five_year_avg_bcf": None,
                "five_year_max_bcf": None,
                "five_year_min_bcf": None,
                "east_bcf": None,
                "midwest_bcf": None,
                "mountain_bcf": None,
                "pacific_bcf": None,
                "south_central_bcf": None,
                "source": "eia_petroleum",
            }
        )

    # Week-over-week deltas on the primary stock level. surprise_bcf mirrors the
    # delta since EIA publishes no consensus survey for petroleum — downstream
    # signals code treats either field as the alt-data signal magnitude.
    for i in range(len(records) - 1):
        curr = records[i].get("total_lower_48_bcf")
        prev = records[i + 1].get("total_lower_48_bcf")
        if curr is not None and prev is not None:
            delta = round(float(curr) - float(prev), 1)
            records[i]["net_change_bcf"] = delta
            records[i]["surprise_bcf"] = delta

    return records
