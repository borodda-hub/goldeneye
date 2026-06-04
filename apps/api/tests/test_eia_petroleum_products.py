"""Phase 17 — EIAPetroleumAdapter generalized to per-symbol product series.

Pure logic tests: series selection + _pivot shape parity across the CL
(two-series) and HO/RB (single-series) paths. No network.
"""
from __future__ import annotations

import pytest

from apps.api.adapters.energy.eia_petroleum import (
    PETROLEUM_SERIES,
    EIAPetroleumAdapter,
    _pivot,
)


def test_series_table_has_three_petroleum_symbols():
    assert set(PETROLEUM_SERIES) == {"CL", "HO", "RB"}


def test_series_selection_per_symbol():
    assert EIAPetroleumAdapter("HO")._series.primary == "WDISTUS1"
    assert EIAPetroleumAdapter("HO")._series.context is None
    assert EIAPetroleumAdapter("RB")._series.primary == "WGTSTUS1"
    assert EIAPetroleumAdapter("RB")._series.context is None
    # CL keeps Cushing primary + total ex-SPR context.
    cl = EIAPetroleumAdapter("CL")
    assert cl._series.primary == "WCESTP31"
    assert cl._series.context == "WCESTUS1"


def test_lowercase_symbol_accepted():
    assert EIAPetroleumAdapter("ho")._series.primary == "WDISTUS1"


def test_unknown_symbol_raises():
    with pytest.raises(ValueError):
        EIAPetroleumAdapter("GC")  # metals have no petroleum series


def test_pivot_single_series_shape_for_products():
    """HO/RB single-series pivot: primary populated, context None, WoW delta."""
    series = PETROLEUM_SERIES["HO"]
    raw = [
        {"period": "2026-05-08", "series": "WDISTUS1", "value": "120000"},
        {"period": "2026-05-01", "series": "WDISTUS1", "value": "118000"},
    ]
    out = _pivot(raw, series)
    assert len(out) == 2
    newest = out[0]
    assert newest["total_lower_48_bcf"] == 120000.0
    assert newest["actual_bcf"] == 120000.0
    assert newest["total_ex_spr_mbbl"] is None
    # WoW delta = 120000 - 118000
    assert newest["net_change_bcf"] == 2000.0
    assert newest["surprise_bcf"] == 2000.0
    assert newest["source"] == "eia_petroleum"


def test_pivot_two_series_shape_for_cl():
    """CL two-series pivot keeps the context (total ex-SPR) field."""
    series = PETROLEUM_SERIES["CL"]
    raw = [
        {"period": "2026-05-08", "series": "WCESTP31", "value": "25000"},
        {"period": "2026-05-08", "series": "WCESTUS1", "value": "440000"},
        {"period": "2026-05-01", "series": "WCESTP31", "value": "24500"},
    ]
    out = _pivot(raw, series)
    newest = out[0]
    assert newest["total_lower_48_bcf"] == 25000.0
    assert newest["total_ex_spr_mbbl"] == 440000.0
    assert newest["net_change_bcf"] == 500.0  # 25000 - 24500


def test_pivot_output_keys_parity_across_symbols():
    """Both paths emit the identical set of keys (shape parity)."""
    ho = _pivot(
        [{"period": "2026-05-08", "series": "WDISTUS1", "value": "120000"}],
        PETROLEUM_SERIES["HO"],
    )[0]
    cl = _pivot(
        [{"period": "2026-05-08", "series": "WCESTP31", "value": "25000"}],
        PETROLEUM_SERIES["CL"],
    )[0]
    assert set(ho.keys()) == set(cl.keys())
