"""Real CFTC COT adapter — Disaggregated Futures-Only via the CFTC Public
Reporting Environment (PRE, Socrata).

API: https://publicreporting.cftc.gov/resource/<resource_code>.json
Resource: Disaggregated Futures-Only Reports (`kh3c-gbw2` per docs/DATA_SOURCES.md
— recheck on the PRE site if Socrata reissues the code).

Returns the same dict shape as MockCFTCAdapter so the rest of the stack
(services/ensemble.py, services/models/xgboost_placeholder.py, etc.) doesn't
care which path produced the row.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any

from apps.api.adapters._http import AdapterHTTPClient

CFTC_BASE_URL = "https://publicreporting.cftc.gov/resource/"
DISAGGREGATED_RESOURCE = "kh3c-gbw2"
NG_MARKET_NAME = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"
NG_CONTRACT_CODE = "023651"

# Socrata column → our dict field. The PRE schema has occasionally renamed
# columns (`_short` vs `_short_all`); we try both via _SHORT_FALLBACKS below.
_COLUMN_MAP: dict[str, str] = {
    "prod_merc_positions_long_all": "producer_long",
    "prod_merc_positions_short_all": "producer_short",
    "swap_positions_long_all": "swap_long",
    "swap_positions_short_all": "swap_short",
    "m_money_positions_long_all": "managed_money_long",
    "m_money_positions_short_all": "managed_money_short",
    "other_rept_positions_long_all": "other_reportable_long",
    "other_rept_positions_short_all": "other_reportable_short",
    "nonrept_positions_long_all": "nonreportable_long",
    "nonrept_positions_short_all": "nonreportable_short",
    "open_interest_all": "open_interest_total",
}

# Fallback column names (older PRE schema). Applied only when the primary
# column is missing from a row.
_SHORT_FALLBACKS: dict[str, str] = {
    "prod_merc_positions_short_all": "prod_merc_positions_short",
    "swap_positions_short_all": "swap__positions_short_all",  # known historical typo
    "m_money_positions_short_all": "m_money_positions_short",
    "other_rept_positions_short_all": "other_rept_positions_short",
    "nonrept_positions_short_all": "nonrept_positions_short",
}

# Weekly data — 24h in-memory cache is more than enough.
_CACHE_TTL_SECONDS = 24 * 60 * 60


def _to_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _column_value(row: dict[str, Any], col: str) -> int | None:
    """Read a column, trying the documented name then any known fallback."""
    if col in row:
        v = _to_int(row[col])
        if v is not None:
            return v
    fallback = _SHORT_FALLBACKS.get(col)
    if fallback and fallback in row:
        return _to_int(row[fallback])
    return None


class CFTCAdapter:
    """Real PositioningDataAdapter implementation reading CFTC PRE."""

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="positioning.cftc.cot")
        self._cache: tuple[float, list[dict[str, Any]]] | None = None

    async def get_cot_reports(self, limit: int = 52) -> list[dict[str, Any]]:
        reports = await self._get_reports_cached()
        return reports[:limit]

    async def get_latest_cot(self) -> dict[str, Any] | None:
        reports = await self._get_reports_cached()
        return reports[0] if reports else None

    async def _get_reports_cached(self) -> list[dict[str, Any]]:
        now = time.time()
        if self._cache is not None:
            cached_at, cached_data = self._cache
            if now - cached_at < _CACHE_TTL_SECONDS:
                return cached_data
        rows = await self._fetch_all()
        reports = self._map(rows)
        self._cache = (now, reports)
        return reports

    async def _fetch_all(self) -> list[dict[str, Any]]:
        # Filter by both name (defensive) and contract code (precise — avoids
        # NG-adjacent markets like "NATURAL GAS LAST DAY FINANCIAL").
        url = CFTC_BASE_URL + DISAGGREGATED_RESOURCE + ".json"
        params: list[tuple[str, str]] = [
            (
                "$where",
                f"cftc_contract_market_code = '{NG_CONTRACT_CODE}' "
                f"AND contract_market_name like 'NATURAL GAS%'",
            ),
            ("$order", "report_date_as_yyyy_mm_dd DESC"),
            ("$limit", "200"),
        ]
        response = await self._client.get(url, params=params)
        body = response.json()
        return body if isinstance(body, list) else []

    @staticmethod
    def _map(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map CFTC PRE rows into our internal cot_report dict shape."""
        records: list[dict[str, Any]] = []
        for row in rows:
            raw_date = row.get("report_date_as_yyyy_mm_dd")
            if not raw_date:
                continue
            report_date = _parse_date(raw_date)
            if report_date is None:
                continue
            release_date = report_date + timedelta(days=3)

            record: dict[str, Any] = {
                "report_date": report_date,
                "release_date": release_date,
                "contract_market_name": row.get("contract_market_name") or NG_MARKET_NAME,
                "cftc_contract_market_code": row.get("cftc_contract_market_code")
                or NG_CONTRACT_CODE,
                "source": "cftc",
            }
            for src_col, dest_field in _COLUMN_MAP.items():
                record[dest_field] = _column_value(row, src_col)
            records.append(record)

        # Already DESC from Socrata, but defensively re-sort.
        records.sort(key=lambda r: r["report_date"], reverse=True)
        return records


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        return None
    # Socrata returns ISO 8601 with "T00:00:00.000" suffix.
    head = raw.split("T", 1)[0]
    try:
        return datetime.strptime(head, "%Y-%m-%d").date()
    except ValueError:
        return None
