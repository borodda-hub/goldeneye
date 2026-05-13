"""Real EIA Petroleum adapter — Weekly crude oil stocks at Cushing, OK.

Used by the signals path when the active instrument is WTI Crude (CL) so
xgboost has alt-data parity with what NG gets from the natural-gas storage
adapter.

Cushing is the canonical delivery point for the NYMEX WTI futures contract,
making its weekly inventory the most price-relevant petroleum series.
EIA series ID: PET.W_EPC0_SAX_YCUOK_MBBL.W (Thousand Barrels, weekly).

This adapter intentionally does NOT persist into the eia_storage_reports
table — that schema is shaped for natural-gas (BCF columns, regional
breakdowns). Phase 14 routes CL alt-data live through this adapter without
DB persistence; a future phase can add an eia_petroleum_stocks hypertable
if backfilled history becomes useful.

Returns the same dict shape as the natural-gas adapter for the two fields
xgboost consumes — `delta_vs_consensus` and `actual_bcf` (here "actual_mbbl",
but the xgboost placeholder is unit-agnostic).
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

from apps.api.adapters._http import AdapterHTTPClient
from apps.api.src.settings import settings

logger = logging.getLogger(__name__)

EIA_BASE_URL = "https://api.eia.gov/v2/"
PETROLEUM_ROUTE = "petroleum/stoc/wstk/data/"

# Cushing OK ending stocks (thousand barrels), weekly.
CUSHING_SERIES = "WCESTP31"  # PADD 1B / Cushing-specific subseries name
# Backstop: total Lower-48 crude stocks ex-SPR, used as the 5-year context.
TOTAL_EX_SPR_SERIES = "WCESTUS1"

# 24h cache — weekly publication on Wednesdays makes more frequent calls wasteful.
_CACHE_TTL_SECONDS = 24 * 60 * 60


class EIAPetroleumAdapter:
    """Real petroleum-stocks adapter for WTI Crude.

    Conforms to the slice of EnergyDataAdapter that signals.py actually
    consumes: `get_latest_storage()` returning a dict with `surprise_bcf`,
    `net_change_bcf`, and an `actual_*` field. The bcf naming is preserved
    so downstream xgboost code doesn't need conditional branches.
    """

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="energy.eia.petroleum.cushing")
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
            reports = _pivot(raw)
        except Exception as exc:
            logger.warning("EIA petroleum fetch failed: %s — empty result.", exc)
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
            ("facets[series][]", CUSHING_SERIES),
            ("facets[series][]", TOTAL_EX_SPR_SERIES),
        ]
        url = EIA_BASE_URL + PETROLEUM_ROUTE
        response = await self._client.get(url, params=params)
        body = response.json()
        data = body.get("response", {}).get("data", [])
        return data if isinstance(data, list) else []


def _pivot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pivot per-(period, series) rows into one record per week_ending.

    Output shape matches the natural-gas adapter so signals.py can read
    `surprise_bcf` and `net_change_bcf` without conditional branches.
    Values are in thousand barrels (mbbl) — the field names retain `_bcf`
    suffix only for shape compatibility; the downstream xgboost placeholder
    is unit-agnostic and uses the magnitudes relative to themselves.
    """
    by_period: dict[str, dict[str, float]] = {}
    for row in rows:
        period = row.get("period")
        series = row.get("series")
        value = row.get("value")
        if period is None or value is None:
            continue
        try:
            fvalue = float(value)
        except (TypeError, ValueError):
            continue
        if series == CUSHING_SERIES:
            by_period.setdefault(period, {})["cushing_mbbl"] = fvalue
        elif series == TOTAL_EX_SPR_SERIES:
            by_period.setdefault(period, {})["total_ex_spr_mbbl"] = fvalue

    records: list[dict[str, Any]] = []
    for period_str in sorted(by_period.keys(), reverse=True):
        try:
            week_ending = date.fromisoformat(period_str)
        except ValueError:
            continue
        fields = by_period[period_str]
        cushing = fields.get("cushing_mbbl")
        total = fields.get("total_ex_spr_mbbl")
        records.append(
            {
                "report_date": week_ending,
                "week_ending": week_ending,
                "total_lower_48_bcf": cushing,  # shape compat — Cushing thousand barrels
                "actual_bcf": cushing,
                "total_ex_spr_mbbl": total,  # canonical CL-side name
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

    # Week-over-week deltas. surprise_bcf gets the same value since EIA
    # doesn't publish a consensus survey for petroleum either — downstream
    # signals code treats either field as the alt-data signal magnitude.
    for i in range(len(records) - 1):
        curr = records[i].get("total_lower_48_bcf")
        prev = records[i + 1].get("total_lower_48_bcf")
        if curr is not None and prev is not None:
            delta = round(float(curr) - float(prev), 1)
            records[i]["net_change_bcf"] = delta
            records[i]["surprise_bcf"] = delta

    return records
