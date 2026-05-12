"""Real EIA adapter — pulls weekly natural-gas working-storage data from EIA Open Data v2.

API docs: https://www.eia.gov/opendata/documentation/APIv2.0.1.pdf
Series IDs sourced from the EIA Weekly Natural Gas Storage Report.

The mock adapter ships a 16-field dict per report; this real adapter fills the
fields EIA actually publishes (Lower-48 total, the five region totals, the
three 5-year stat lines) and leaves `consensus_estimate` / `surprise_bcf`
as None because EIA does not publish analyst-survey consensus — that's a
Bloomberg/Refinitiv data point and out of scope here.

`net_change_bcf` is derived as week-over-week delta of `total_lower_48_bcf`.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

from apps.api.adapters._http import AdapterHTTPClient
from apps.api.src.settings import settings

EIA_BASE_URL = "https://api.eia.gov/v2/"
STORAGE_ROUTE = "natural-gas/stor/wkly/data/"

# Working-gas-in-storage series IDs (NG weekly).
SERIES_TOTAL = "NW2_EPG0_SWO_R48_BCF"
SERIES_EAST = "NW2_EPG0_SWO_R31_BCF"
SERIES_MIDWEST = "NW2_EPG0_SWO_R32_BCF"
SERIES_MOUNTAIN = "NW2_EPG0_SWO_R33_BCF"
SERIES_PACIFIC = "NW2_EPG0_SWO_R34_BCF"
SERIES_SOUTH_CENTRAL = "NW2_EPG0_SWO_R35_BCF"

# Five-year statistics (Lower-48).
SERIES_5YR_AVG = "NW2_EPG0_SAO_R48_BCF"
SERIES_5YR_MAX = "NW2_EPG0_SMX_R48_BCF"
SERIES_5YR_MIN = "NW2_EPG0_SMN_R48_BCF"

_SERIES_TO_FIELD: dict[str, str] = {
    SERIES_TOTAL: "total_lower_48_bcf",
    SERIES_EAST: "east_bcf",
    SERIES_MIDWEST: "midwest_bcf",
    SERIES_MOUNTAIN: "mountain_bcf",
    SERIES_PACIFIC: "pacific_bcf",
    SERIES_SOUTH_CENTRAL: "south_central_bcf",
    SERIES_5YR_AVG: "five_year_avg_bcf",
    SERIES_5YR_MAX: "five_year_max_bcf",
    SERIES_5YR_MIN: "five_year_min_bcf",
}

_REPORT_FIELDS = (
    "total_lower_48_bcf",
    "east_bcf",
    "midwest_bcf",
    "mountain_bcf",
    "pacific_bcf",
    "south_central_bcf",
    "five_year_avg_bcf",
    "five_year_max_bcf",
    "five_year_min_bcf",
)

# Weekly data only updates Thursdays — 24h in-memory cache is plenty.
_CACHE_TTL_SECONDS = 24 * 60 * 60


class EIAAdapter:
    """Real EnergyDataAdapter implementation reading EIA Open Data v2."""

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="energy.eia.storage")
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
        raw = await self._fetch_all()
        reports = self._pivot(raw)
        self._cache = (now, reports)
        return reports

    async def _fetch_all(self) -> list[dict[str, Any]]:
        api_key = settings.eia_api_key
        if not api_key:
            return []

        params: list[tuple[str, str]] = [
            ("api_key", api_key),
            ("frequency", "weekly"),
            ("data[]", "value"),
            ("sort[0][column]", "period"),
            ("sort[0][direction]", "desc"),
            # 9 series × ~110 weeks ≈ 990 rows, leaves headroom.
            ("length", "1100"),
        ]
        for series in _SERIES_TO_FIELD.keys():
            params.append(("facets[series][]", series))

        url = EIA_BASE_URL + STORAGE_ROUTE
        response = await self._client.get(url, params=params)
        body = response.json()
        data = body.get("response", {}).get("data", [])
        return data if isinstance(data, list) else []

    @staticmethod
    def _pivot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pivot per-(period, series) rows into one record per week_ending date."""
        by_period: dict[str, dict[str, float]] = {}
        for row in rows:
            period = row.get("period")
            series = row.get("series")
            value = row.get("value")
            if period is None or series not in _SERIES_TO_FIELD or value is None:
                continue
            try:
                fvalue = float(value)
            except (TypeError, ValueError):
                continue
            field = _SERIES_TO_FIELD[series]
            by_period.setdefault(period, {})[field] = fvalue

        records: list[dict[str, Any]] = []
        for period_str in sorted(by_period.keys(), reverse=True):
            try:
                week_ending = date.fromisoformat(period_str)
            except ValueError:
                continue
            # EIA publishes Thursday after the Friday week-ending.
            report_date = week_ending + timedelta(days=6)
            fields = by_period[period_str]
            record: dict[str, Any] = {
                "report_date": report_date,
                "week_ending": week_ending,
                "net_change_bcf": None,  # filled below
                # EIA does not publish analyst-survey consensus.
                "consensus_estimate": None,
                "surprise_bcf": None,
                "source": "eia",
            }
            for field in _REPORT_FIELDS:
                record[field] = fields.get(field)
            records.append(record)

        # Week-over-week change. Records are sorted newest-first.
        for i in range(len(records) - 1):
            curr = records[i]["total_lower_48_bcf"]
            prev = records[i + 1]["total_lower_48_bcf"]
            if curr is not None and prev is not None:
                records[i]["net_change_bcf"] = round(curr - prev, 1)

        return records
