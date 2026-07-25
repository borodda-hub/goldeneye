"""Phase 31a — paginated range-fetch paths on the real COT/EIA adapters.

Pure logic with a stubbed HTTP client (no network): pagination actually
pages, the query filters carry the requested range, mapping matches the live
path's shape, and every adapter still satisfies its protocol.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import pytest

import apps.api.adapters.energy.eia as eia_mod
import apps.api.adapters.positioning.cftc as cftc_mod
from apps.api.adapters.base import EnergyDataAdapter, PositioningDataAdapter
from apps.api.adapters.energy.eia import EIAAdapter
from apps.api.adapters.energy.eia_petroleum import EIAPetroleumAdapter
from apps.api.adapters.energy.mock_eia import MockEIAAdapter
from apps.api.adapters.energy.null_energy import NullEnergyAdapter
from apps.api.adapters.positioning.cftc import CFTCAdapter
from apps.api.adapters.positioning.mock_cftc import MockCFTCAdapter


class _FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    """Stands in for AdapterHTTPClient; records params, serves canned pages."""

    def __init__(self, pages: list[Any]) -> None:
        self.pages = pages
        self.calls: list[list[tuple[str, str]]] = []

    async def get(self, url: str = "", **kwargs: Any) -> _FakeResponse:
        params = kwargs.get("params") or []
        self.calls.append(list(params))
        idx = len(self.calls) - 1
        payload = self.pages[idx] if idx < len(self.pages) else self.pages[-1]
        return _FakeResponse(payload)


def _param(params: list[tuple[str, str]], key: str) -> str | None:
    for k, v in params:
        if k == key:
            return v
    return None


# ── CFTC range path ───────────────────────────────────────────────────────


def _socrata_row(report_date: date) -> dict[str, Any]:
    return {
        "report_date_as_yyyy_mm_dd": f"{report_date.isoformat()}T00:00:00.000",
        "contract_market_name": "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE",
        "cftc_contract_market_code": "023651",
        "m_money_positions_long_all": "100000",
        "m_money_positions_short_all": "40000",
        "open_interest_all": "1400000",
    }


def test_cftc_range_paginates_and_maps(monkeypatch):
    monkeypatch.setattr(cftc_mod, "_RANGE_PAGE_SIZE", 2)
    # Page 0: full page of 2 → keep paging. Page 1: short page of 1 → stop.
    pages = [
        [_socrata_row(date(2026, 4, 14)), _socrata_row(date(2026, 4, 7))],
        [_socrata_row(date(2026, 3, 31))],
    ]
    adapter = CFTCAdapter("NG")
    adapter._client = _FakeClient(pages)  # type: ignore[assignment]

    rows = asyncio.run(adapter.get_cot_reports_range(date(2026, 3, 1), date(2026, 4, 30)))

    assert len(rows) == 3
    assert [c and _param(c, "$offset") for c in adapter._client.calls] == ["0", "2"]
    where = _param(adapter._client.calls[0], "$where") or ""
    assert "cftc_contract_market_code = '023651'" in where
    assert "report_date_as_yyyy_mm_dd >= '2026-03-01T00:00:00.000'" in where
    assert "report_date_as_yyyy_mm_dd <= '2026-04-30T23:59:59.000'" in where
    # Same mapping as the live path: Tue report → Fri release, ints parsed.
    assert rows[0]["report_date"] == date(2026, 4, 14)
    assert rows[0]["release_date"] == date(2026, 4, 17)
    assert rows[0]["managed_money_long"] == 100_000


def test_cftc_range_single_short_page(monkeypatch):
    monkeypatch.setattr(cftc_mod, "_RANGE_PAGE_SIZE", 1000)
    adapter = CFTCAdapter("NG")
    adapter._client = _FakeClient([[_socrata_row(date(2026, 4, 14))]])  # type: ignore[assignment]
    rows = asyncio.run(adapter.get_cot_reports_range(date(2026, 4, 1), date(2026, 4, 30)))
    assert len(rows) == 1
    assert len(adapter._client.calls) == 1  # short first page → no second call


# ── EIA range path ────────────────────────────────────────────────────────


def _eia_row(week_ending: date, value: float) -> dict[str, Any]:
    return {
        "period": week_ending.isoformat(),
        "series": eia_mod.SERIES_TOTAL,
        "value": str(value),
    }


def test_eia_range_filters_and_keeps_boundary_net_change(monkeypatch):
    monkeypatch.setattr(eia_mod.settings, "eia_api_key", "test-key")
    start, end = date(2026, 4, 3), date(2026, 4, 17)
    # Fetch is padded 2 weeks before `start` so the oldest requested week
    # keeps its WoW delta after the pivot drops its own boundary row.
    payload = {
        "response": {
            "data": [
                _eia_row(date(2026, 4, 17), 1540.0),
                _eia_row(date(2026, 4, 10), 1520.0),
                _eia_row(date(2026, 4, 3), 1500.0),
                _eia_row(date(2026, 3, 27), 1480.0),  # padding week
            ]
        }
    }
    adapter = EIAAdapter()
    adapter._client = _FakeClient([payload])  # type: ignore[assignment]

    rows = asyncio.run(adapter.get_storage_reports_range(start, end))

    params = adapter._client.calls[0]
    assert _param(params, "start") == (start - timedelta(days=14)).isoformat()
    assert _param(params, "end") == end.isoformat()
    # Trimmed to the requested range — padding week excluded...
    assert [r["week_ending"] for r in rows] == [
        date(2026, 4, 17),
        date(2026, 4, 10),
        date(2026, 4, 3),
    ]
    # ...but its value still fed the oldest requested week's WoW change.
    assert rows[-1]["net_change_bcf"] == 20.0
    assert all(r["net_change_bcf"] is not None for r in rows)
    # Real-EIA shape: no consensus survey fields.
    assert rows[0]["surprise_bcf"] is None


def test_eia_range_paginates(monkeypatch):
    monkeypatch.setattr(eia_mod.settings, "eia_api_key", "test-key")
    monkeypatch.setattr(eia_mod, "_RANGE_PAGE_SIZE", 2)
    pages = [
        {
            "response": {
                "data": [
                    _eia_row(date(2026, 4, 17), 1540.0),
                    _eia_row(date(2026, 4, 10), 1520.0),
                ]
            }
        },
        {"response": {"data": [_eia_row(date(2026, 4, 3), 1500.0)]}},
    ]
    adapter = EIAAdapter()
    adapter._client = _FakeClient(pages)  # type: ignore[assignment]
    rows = asyncio.run(adapter.get_storage_reports_range(date(2026, 4, 1), date(2026, 4, 30)))
    assert [_param(c, "offset") for c in adapter._client.calls] == ["0", "2"]
    assert len(rows) == 2  # 3 weeks fetched − 1 boundary drop


def test_eia_range_without_key_returns_empty():
    adapter = EIAAdapter()
    if eia_mod.settings.eia_api_key:
        pytest.skip("EIA_API_KEY set in this environment")
    assert asyncio.run(adapter.get_storage_reports_range(date(2026, 4, 1), date(2026, 4, 30))) == []


# ── Mock parity + protocol conformance ────────────────────────────────────


def test_mock_range_methods_filter():
    cot = asyncio.run(MockCFTCAdapter().get_cot_reports_range(date(2026, 4, 1), date(2026, 4, 30)))
    assert cot
    assert all(date(2026, 4, 1) <= r["report_date"] <= date(2026, 4, 30) for r in cot)
    storage = asyncio.run(
        MockEIAAdapter().get_storage_reports_range(date(2026, 4, 1), date(2026, 4, 30))
    )
    assert storage
    assert all(date(2026, 4, 1) <= r["week_ending"] <= date(2026, 4, 30) for r in storage)


def test_all_adapters_still_satisfy_protocols():
    for positioning in (MockCFTCAdapter(), CFTCAdapter("NG")):
        assert isinstance(positioning, PositioningDataAdapter)
    for energy in (MockEIAAdapter(), EIAAdapter(), NullEnergyAdapter(), EIAPetroleumAdapter("CL")):
        assert isinstance(energy, EnergyDataAdapter)
