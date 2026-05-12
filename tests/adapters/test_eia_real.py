"""Unit tests for the real EIA adapter — pivot, net-change derivation, missing-key path."""
from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.adapters.energy.eia import (
    EIAAdapter,
    SERIES_EAST,
    SERIES_MIDWEST,
    SERIES_MOUNTAIN,
    SERIES_PACIFIC,
    SERIES_SOUTH_CENTRAL,
    SERIES_TOTAL,
    SERIES_5YR_AVG,
    SERIES_5YR_MAX,
    SERIES_5YR_MIN,
)


def _eia_rows(period: str, total: float) -> list[dict]:
    """Build a complete set of series rows for a single period."""
    # Regional splits roughly match EIA proportions; values arbitrary for test.
    return [
        {"period": period, "series": SERIES_TOTAL, "value": total},
        {"period": period, "series": SERIES_EAST, "value": round(total * 0.18, 1)},
        {"period": period, "series": SERIES_MIDWEST, "value": round(total * 0.24, 1)},
        {"period": period, "series": SERIES_MOUNTAIN, "value": round(total * 0.05, 1)},
        {"period": period, "series": SERIES_PACIFIC, "value": round(total * 0.07, 1)},
        {"period": period, "series": SERIES_SOUTH_CENTRAL, "value": round(total * 0.46, 1)},
        {"period": period, "series": SERIES_5YR_AVG, "value": round(total * 0.98, 1)},
        {"period": period, "series": SERIES_5YR_MAX, "value": round(total * 1.10, 1)},
        {"period": period, "series": SERIES_5YR_MIN, "value": round(total * 0.86, 1)},
    ]


def test_pivot_assembles_one_record_per_period():
    rows = _eia_rows("2026-05-02", 2150.4) + _eia_rows("2026-04-25", 2100.1)
    records = EIAAdapter._pivot(rows)
    assert len(records) == 2
    newest = records[0]
    assert newest["week_ending"] == date(2026, 5, 2)
    # week_ending is the Friday; report_date is the following Thursday (+6 days).
    assert newest["report_date"] == date(2026, 5, 8)
    assert newest["total_lower_48_bcf"] == 2150.4
    assert newest["east_bcf"] == round(2150.4 * 0.18, 1)
    assert newest["source"] == "eia"


def test_pivot_orders_newest_first():
    rows = _eia_rows("2026-04-25", 2100.1) + _eia_rows("2026-05-02", 2150.4)
    records = EIAAdapter._pivot(rows)
    assert [r["week_ending"] for r in records] == [date(2026, 5, 2), date(2026, 4, 25)]


def test_net_change_is_wow_delta_of_total():
    rows = _eia_rows("2026-05-02", 2150.4) + _eia_rows("2026-04-25", 2100.1)
    records = EIAAdapter._pivot(rows)
    assert records[0]["net_change_bcf"] == round(2150.4 - 2100.1, 1)
    # Oldest record has no prior week → net_change_bcf is None.
    assert records[-1]["net_change_bcf"] is None


def test_consensus_and_surprise_are_none_on_real_path():
    """EIA does not publish analyst-survey consensus."""
    rows = _eia_rows("2026-05-02", 2150.4)
    records = EIAAdapter._pivot(rows)
    assert records[0]["consensus_estimate"] is None
    assert records[0]["surprise_bcf"] is None


def test_pivot_skips_unknown_series():
    rows = _eia_rows("2026-05-02", 2150.4) + [
        {"period": "2026-05-02", "series": "SOME_OTHER_SERIES", "value": 99.0}
    ]
    records = EIAAdapter._pivot(rows)
    assert len(records) == 1
    # The unknown series didn't crash the pivot or appear as a field.
    assert "some_other_series" not in records[0]


def test_pivot_tolerates_non_numeric_values():
    rows = _eia_rows("2026-05-02", 2150.4)
    rows.append({"period": "2026-05-02", "series": SERIES_TOTAL, "value": "garbage"})
    records = EIAAdapter._pivot(rows)
    # The earlier good value sticks.
    assert records[0]["total_lower_48_bcf"] == 2150.4


def test_pivot_skips_invalid_period():
    rows = [
        {"period": "not-a-date", "series": SERIES_TOTAL, "value": 1000.0},
        *_eia_rows("2026-05-02", 2150.4),
    ]
    records = EIAAdapter._pivot(rows)
    assert len(records) == 1
    assert records[0]["week_ending"] == date(2026, 5, 2)


def test_fetch_all_returns_empty_when_api_key_missing(monkeypatch):
    """No EIA_API_KEY → empty list, no HTTP call."""
    from apps.api.src import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "eia_api_key", "")
    adapter = EIAAdapter()
    # No HTTP mock set up — if the adapter calls out, this test would error.
    result = asyncio.run(adapter._fetch_all())
    assert result == []


def test_get_latest_storage_returns_newest(monkeypatch):
    """End-to-end through the cached path with a mocked HTTP response."""
    from apps.api.src import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "eia_api_key", "dummy-key")

    canned_body = {
        "response": {
            "data": _eia_rows("2026-05-02", 2150.4) + _eia_rows("2026-04-25", 2100.1)
        }
    }

    class _FakeResponse:
        def json(self):
            return canned_body

    adapter = EIAAdapter()
    with patch.object(adapter._client, "get", new=AsyncMock(return_value=_FakeResponse())):
        latest = asyncio.run(adapter.get_latest_storage())
        assert latest is not None
        assert latest["week_ending"] == date(2026, 5, 2)
        assert latest["total_lower_48_bcf"] == 2150.4
        assert latest["net_change_bcf"] == round(2150.4 - 2100.1, 1)


def test_cache_hits_avoid_second_http_call(monkeypatch):
    from apps.api.src import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "eia_api_key", "dummy-key")

    canned_body = {"response": {"data": _eia_rows("2026-05-02", 2150.4)}}

    class _FakeResponse:
        def json(self):
            return canned_body

    adapter = EIAAdapter()
    mock_get = AsyncMock(return_value=_FakeResponse())
    with patch.object(adapter._client, "get", new=mock_get):
        asyncio.run(adapter.get_storage_reports(limit=10))
        asyncio.run(adapter.get_storage_reports(limit=10))
    assert mock_get.await_count == 1


def test_registry_falls_back_to_mock_when_key_missing(monkeypatch):
    """ADAPTER_ENERGY=eia + no EIA_API_KEY → mock, not real."""
    from apps.api.adapters import registry
    from apps.api.adapters.energy.mock_eia import MockEIAAdapter
    from apps.api.src import settings as settings_module

    registry.get_energy.cache_clear()
    monkeypatch.setattr(settings_module.settings, "adapter_energy", "eia")
    monkeypatch.setattr(settings_module.settings, "eia_api_key", "")
    instance = registry.get_energy()
    registry.get_energy.cache_clear()
    assert isinstance(instance, MockEIAAdapter)


def test_registry_returns_real_when_key_present(monkeypatch):
    from apps.api.adapters import registry
    from apps.api.adapters.energy.eia import EIAAdapter
    from apps.api.src import settings as settings_module

    registry.get_energy.cache_clear()
    monkeypatch.setattr(settings_module.settings, "adapter_energy", "eia")
    monkeypatch.setattr(settings_module.settings, "eia_api_key", "dummy")
    instance = registry.get_energy()
    registry.get_energy.cache_clear()
    assert isinstance(instance, EIAAdapter)
