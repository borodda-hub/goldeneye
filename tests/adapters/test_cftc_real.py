"""Unit tests for the real CFTC COT adapter — column mapping, fallback names, cache."""
from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.adapters.positioning.cftc import CFTCAdapter, NG_MARKET_NAME, NG_CONTRACT_CODE


def _socrata_row(report_date: str = "2026-05-05T00:00:00.000") -> dict:
    """A row in the canonical PRE schema with `_all` short-position columns."""
    return {
        "report_date_as_yyyy_mm_dd": report_date,
        "contract_market_name": NG_MARKET_NAME,
        "cftc_contract_market_code": NG_CONTRACT_CODE,
        "prod_merc_positions_long_all": "400000",
        "prod_merc_positions_short_all": "420000",
        "swap_positions_long_all": "300000",
        "swap_positions_short_all": "280000",
        "m_money_positions_long_all": "180000",
        "m_money_positions_short_all": "130000",
        "other_rept_positions_long_all": "50000",
        "other_rept_positions_short_all": "40000",
        "nonrept_positions_long_all": "70000",
        "nonrept_positions_short_all": "75000",
        "open_interest_all": "1400000",
    }


def test_map_extracts_canonical_columns():
    records = CFTCAdapter._map([_socrata_row()])
    assert len(records) == 1
    rec = records[0]
    assert rec["report_date"] == date(2026, 5, 5)
    # release_date = report_date + 3 days (Friday).
    assert rec["release_date"] == date(2026, 5, 8)
    assert rec["managed_money_long"] == 180000
    assert rec["managed_money_short"] == 130000
    assert rec["producer_long"] == 400000
    assert rec["swap_long"] == 300000
    assert rec["other_reportable_long"] == 50000
    assert rec["nonreportable_long"] == 70000
    assert rec["open_interest_total"] == 1400000
    assert rec["source"] == "cftc"
    assert rec["contract_market_name"] == NG_MARKET_NAME
    assert rec["cftc_contract_market_code"] == NG_CONTRACT_CODE


def test_map_falls_back_to_legacy_short_columns():
    """Older PRE schema dropped the `_all` suffix on short positions."""
    row = _socrata_row()
    # Remove canonical short cols, add legacy ones.
    legacy_subs = {
        "prod_merc_positions_short_all": "prod_merc_positions_short",
        "m_money_positions_short_all": "m_money_positions_short",
        "other_rept_positions_short_all": "other_rept_positions_short",
        "nonrept_positions_short_all": "nonrept_positions_short",
    }
    for canonical, legacy in legacy_subs.items():
        row[legacy] = row.pop(canonical)
    records = CFTCAdapter._map([row])
    rec = records[0]
    assert rec["managed_money_short"] == 130000
    assert rec["producer_short"] == 420000
    assert rec["other_reportable_short"] == 40000
    assert rec["nonreportable_short"] == 75000


def test_map_returns_none_for_missing_columns():
    sparse = {
        "report_date_as_yyyy_mm_dd": "2026-05-05",
        "contract_market_name": NG_MARKET_NAME,
        "cftc_contract_market_code": NG_CONTRACT_CODE,
        "m_money_positions_long_all": "180000",
        # Everything else missing.
    }
    rec = CFTCAdapter._map([sparse])[0]
    assert rec["managed_money_long"] == 180000
    assert rec["producer_long"] is None
    assert rec["swap_short"] is None
    assert rec["open_interest_total"] is None


def test_map_skips_rows_with_no_report_date():
    rows = [_socrata_row(), {"some": "garbage"}, _socrata_row("2026-04-28T00:00:00.000")]
    records = CFTCAdapter._map(rows)
    assert len(records) == 2
    assert [r["report_date"] for r in records] == [date(2026, 5, 5), date(2026, 4, 28)]


def test_map_orders_newest_first():
    rows = [_socrata_row("2026-04-28"), _socrata_row("2026-05-05"), _socrata_row("2026-04-21")]
    records = CFTCAdapter._map(rows)
    assert [r["report_date"] for r in records] == [
        date(2026, 5, 5),
        date(2026, 4, 28),
        date(2026, 4, 21),
    ]


def test_map_tolerates_non_numeric_values():
    row = _socrata_row()
    row["open_interest_all"] = "not-a-number"
    rec = CFTCAdapter._map([row])[0]
    assert rec["open_interest_total"] is None
    # Other fields still parse.
    assert rec["managed_money_long"] == 180000


def test_get_latest_cot_returns_newest_via_mocked_http():
    canned = [_socrata_row("2026-05-05"), _socrata_row("2026-04-28")]
    adapter = CFTCAdapter()

    class _FakeResponse:
        def json(self):
            return canned

    with patch.object(adapter._client, "get", new=AsyncMock(return_value=_FakeResponse())):
        latest = asyncio.run(adapter.get_latest_cot())
        assert latest is not None
        assert latest["report_date"] == date(2026, 5, 5)
        assert latest["managed_money_long"] == 180000


def test_cache_hits_avoid_second_http_call():
    canned = [_socrata_row("2026-05-05")]
    adapter = CFTCAdapter()

    class _FakeResponse:
        def json(self):
            return canned

    mock_get = AsyncMock(return_value=_FakeResponse())
    with patch.object(adapter._client, "get", new=mock_get):
        asyncio.run(adapter.get_cot_reports(limit=10))
        asyncio.run(adapter.get_cot_reports(limit=10))
    assert mock_get.await_count == 1
