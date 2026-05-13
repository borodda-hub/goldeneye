"""Phase 14 step 4 — EIA petroleum (Cushing crude stocks) adapter tests."""
from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

from apps.api.adapters.energy.eia_petroleum import (
    CUSHING_SERIES,
    EIAPetroleumAdapter,
    TOTAL_EX_SPR_SERIES,
    _pivot,
)


def _eia_row(period: str, series: str, value: float) -> dict:
    return {"period": period, "series": series, "value": value}


# ── Pivot ─────────────────────────────────────────────────────────────────


def test_pivot_groups_cushing_and_total_by_week():
    rows = [
        _eia_row("2026-05-08", CUSHING_SERIES, 22500.0),
        _eia_row("2026-05-08", TOTAL_EX_SPR_SERIES, 412300.0),
        _eia_row("2026-05-01", CUSHING_SERIES, 23000.0),
        _eia_row("2026-05-01", TOTAL_EX_SPR_SERIES, 414100.0),
    ]
    out = _pivot(rows)
    assert len(out) == 2
    # Newest first.
    assert out[0]["week_ending"] == date(2026, 5, 8)
    assert out[0]["total_lower_48_bcf"] == 22500.0  # shape-compat: Cushing in this field
    assert out[0]["total_ex_spr_mbbl"] == 412300.0
    # Week-over-week change populated for the newer record.
    assert out[0]["net_change_bcf"] == -500.0  # 22500 - 23000
    assert out[0]["surprise_bcf"] == -500.0
    # Oldest record's delta stays None.
    assert out[1]["net_change_bcf"] is None
    assert out[1]["surprise_bcf"] is None


def test_pivot_skips_unknown_series():
    rows = [
        _eia_row("2026-05-08", "SOME_OTHER_SERIES", 12345.0),
        _eia_row("2026-05-08", CUSHING_SERIES, 22000.0),
    ]
    out = _pivot(rows)
    assert len(out) == 1
    assert out[0]["total_lower_48_bcf"] == 22000.0


def test_pivot_tolerates_non_numeric_values():
    rows = [
        _eia_row("2026-05-08", CUSHING_SERIES, "not-a-number"),
        _eia_row("2026-05-01", CUSHING_SERIES, 23000.0),
    ]
    out = _pivot(rows)
    # The malformed row is skipped; only May 1 survives.
    assert len(out) == 1
    assert out[0]["week_ending"] == date(2026, 5, 1)


def test_pivot_skips_invalid_period_strings():
    rows = [
        _eia_row("not-a-date", CUSHING_SERIES, 22000.0),
        _eia_row("2026-05-08", CUSHING_SERIES, 22500.0),
    ]
    out = _pivot(rows)
    assert len(out) == 1
    assert out[0]["week_ending"] == date(2026, 5, 8)


def test_pivot_records_carry_petroleum_source():
    rows = [_eia_row("2026-05-08", CUSHING_SERIES, 22500.0)]
    out = _pivot(rows)
    assert out[0]["source"] == "eia_petroleum"


# ── Fetch + cache ─────────────────────────────────────────────────────────


def test_get_latest_storage_returns_newest_record():
    adapter = EIAPetroleumAdapter()
    canned_body = {
        "response": {
            "data": [
                _eia_row("2026-05-08", CUSHING_SERIES, 22500.0),
                _eia_row("2026-05-01", CUSHING_SERIES, 23000.0),
            ]
        }
    }

    class _FakeResponse:
        def json(self):
            return canned_body

    with patch("apps.api.adapters.energy.eia_petroleum.settings") as mock_settings:
        mock_settings.eia_api_key = "test-key"
        with patch.object(adapter._client, "get", new=AsyncMock(return_value=_FakeResponse())):
            latest = asyncio.run(adapter.get_latest_storage())
    assert latest is not None
    assert latest["week_ending"] == date(2026, 5, 8)
    assert latest["total_lower_48_bcf"] == 22500.0


def test_no_api_key_returns_empty():
    adapter = EIAPetroleumAdapter()
    with patch("apps.api.adapters.energy.eia_petroleum.settings") as mock_settings:
        mock_settings.eia_api_key = ""
        latest = asyncio.run(adapter.get_latest_storage())
    assert latest is None


def test_http_failure_returns_empty_without_raising():
    adapter = EIAPetroleumAdapter()
    with patch("apps.api.adapters.energy.eia_petroleum.settings") as mock_settings:
        mock_settings.eia_api_key = "test-key"
        with patch.object(
            adapter._client, "get", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            latest = asyncio.run(adapter.get_latest_storage())
    assert latest is None


# ── Registry routing ──────────────────────────────────────────────────────


def test_registry_get_energy_returns_petroleum_for_cl():
    from apps.api.adapters.registry import get_energy

    # Bypass the @lru_cache for this assertion by clearing it.
    get_energy.cache_clear()

    with patch("apps.api.adapters.registry.settings") as mock_settings:
        mock_settings.adapter_energy = "eia"
        mock_settings.eia_api_key = "test-key"
        adapter = get_energy("CL")
    assert isinstance(adapter, EIAPetroleumAdapter)


def test_registry_get_energy_returns_natural_gas_for_ng():
    from apps.api.adapters.energy.eia import EIAAdapter
    from apps.api.adapters.registry import get_energy

    get_energy.cache_clear()
    with patch("apps.api.adapters.registry.settings") as mock_settings:
        mock_settings.adapter_energy = "eia"
        mock_settings.eia_api_key = "test-key"
        adapter = get_energy("NG")
    assert isinstance(adapter, EIAAdapter)


def test_registry_get_energy_falls_back_to_mock_without_key():
    from apps.api.adapters.energy.mock_eia import MockEIAAdapter
    from apps.api.adapters.registry import get_energy

    get_energy.cache_clear()
    with patch("apps.api.adapters.registry.settings") as mock_settings:
        mock_settings.adapter_energy = "eia"
        mock_settings.eia_api_key = ""
        adapter = get_energy("CL")
    assert isinstance(adapter, MockEIAAdapter)
