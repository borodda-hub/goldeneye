"""Unit tests for the moving-average indicator family (Phase 15a)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apps.api.services.indicators import (
    IndicatorSpec,
    UnknownIndicatorError,
    VolumeRequiredError,
    compute,
    registered_types,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "ma_reference.json").read_text()
)


def _frame(closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    idx = pd.DatetimeIndex([start + timedelta(days=i) for i in range(len(closes))])
    data = {
        "open": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
    }
    if volumes is not None:
        data["volume"] = volumes
    return pd.DataFrame(data, index=idx)


def _values(spec: IndicatorSpec, df: pd.DataFrame) -> list[float | None]:
    return [p.v for p in compute(spec, df).lines[0].points]


# ---------- registry ----------


def test_all_seven_mas_registered():
    assert set(registered_types()) >= {"sma", "ema", "wma", "hma", "dema", "tema", "vwma"}


def test_unknown_type_raises():
    df = _frame(FIXTURE["closes"])
    with pytest.raises(UnknownIndicatorError):
        compute(IndicatorSpec(type="not_real", params={"period": 5}), df)


# ---------- SMA ----------


def test_sma_matches_reference():
    df = _frame(FIXTURE["closes"])
    got = _values(IndicatorSpec(type="sma", params={"period": 3}), df)
    expected = FIXTURE["sma_period_3"]
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        if e is None:
            assert g is None
        else:
            assert g == pytest.approx(e, rel=1e-9)


def test_sma_period_1_equals_close():
    closes = [1.0, 2.0, 3.0, 4.0]
    df = _frame(closes)
    got = _values(IndicatorSpec(type="sma", params={"period": 1}), df)
    assert got == closes


def test_sma_constant_input_constant_output():
    df = _frame([7.5] * 10)
    got = _values(IndicatorSpec(type="sma", params={"period": 4}), df)
    assert got[:3] == [None, None, None]
    for v in got[3:]:
        assert v == pytest.approx(7.5)


def test_period_longer_than_data_all_none():
    df = _frame([1.0, 2.0, 3.0])
    got = _values(IndicatorSpec(type="sma", params={"period": 10}), df)
    assert got == [None, None, None]


# ---------- EMA ----------


def test_ema_matches_reference():
    df = _frame(FIXTURE["closes"])
    got = _values(IndicatorSpec(type="ema", params={"period": 3}), df)
    expected = FIXTURE["ema_period_3"]
    for g, e in zip(got, expected):
        if e is None:
            assert g is None
        else:
            assert g == pytest.approx(e, rel=1e-9)


def test_ema_long_constant_converges():
    df = _frame([5.0] * 50)
    got = _values(IndicatorSpec(type="ema", params={"period": 10}), df)
    # Trailing values converge to the constant
    assert got[-1] == pytest.approx(5.0)


# ---------- WMA ----------


def test_wma_matches_reference():
    df = _frame(FIXTURE["closes"])
    got = _values(IndicatorSpec(type="wma", params={"period": 3}), df)
    expected = FIXTURE["wma_period_3"]
    for g, e in zip(got, expected):
        if e is None:
            assert g is None
        else:
            assert g == pytest.approx(e, rel=1e-9)


# ---------- HMA / DEMA / TEMA: formula-composition checks ----------


def _ewm(values: list[float], period: int) -> list[float]:
    return list(
        pd.Series(values).ewm(span=period, adjust=False).mean().to_numpy()
    )


def test_dema_equals_two_ema_minus_ema_of_ema():
    closes = [10, 11, 12, 11, 13, 14, 15, 14, 16, 17, 18, 17, 19, 20, 21]
    df = _frame([float(c) for c in closes])
    period = 4
    got = _values(IndicatorSpec(type="dema", params={"period": period}), df)

    e1 = _ewm([float(c) for c in closes], period)
    e2 = _ewm(e1, period)
    expected = [2 * a - b for a, b in zip(e1, e2)]

    warmup = 2 * (period - 1)
    for i in range(warmup):
        assert got[i] is None
    for i in range(warmup, len(closes)):
        assert got[i] == pytest.approx(expected[i], rel=1e-9)


def test_tema_equals_3e1_minus_3e2_plus_e3():
    closes = [10, 11, 12, 11, 13, 14, 15, 14, 16, 17, 18, 17, 19, 20, 21, 22, 21, 23]
    df = _frame([float(c) for c in closes])
    period = 4
    got = _values(IndicatorSpec(type="tema", params={"period": period}), df)

    e1 = _ewm([float(c) for c in closes], period)
    e2 = _ewm(e1, period)
    e3 = _ewm(e2, period)
    expected = [3 * a - 3 * b + c for a, b, c in zip(e1, e2, e3)]

    warmup = 3 * (period - 1)
    for i in range(warmup):
        assert got[i] is None
    for i in range(warmup, len(closes)):
        assert got[i] == pytest.approx(expected[i], rel=1e-9)


def test_hma_matches_wma_composition():
    """HMA = WMA(2*WMA(period/2) - WMA(period), sqrt(period))."""
    closes = [10.0, 11, 12, 11, 13, 14, 15, 14, 16, 17, 18, 17, 19, 20, 21, 22]
    df = _frame(closes)
    period = 9
    got = _values(IndicatorSpec(type="hma", params={"period": period}), df)

    def _wma(values: list[float], n: int) -> list[float | None]:
        if n == 1:
            return list(values)
        weights = np.arange(1, n + 1, dtype=float)
        w_sum = weights.sum()
        out: list[float | None] = []
        for i in range(len(values)):
            if i < n - 1:
                out.append(None)
            else:
                window = np.array(values[i - n + 1 : i + 1], dtype=float)
                out.append(float(np.dot(window, weights) / w_sum))
        return out

    half = max(1, period // 2)
    sqrt_n = max(1, int(round(np.sqrt(period))))
    w_half = _wma(closes, half)
    w_full = _wma(closes, period)
    diff = [
        (2 * a - b) if (a is not None and b is not None) else None
        for a, b in zip(w_half, w_full)
    ]
    # WMA over a series with leading Nones: leading values stay None until
    # there are sqrt_n consecutive numbers — but since the longest input gap
    # is (period - 1), the first non-None index is (period - 1) + (sqrt_n - 1).
    first_defined = (period - 1) + (sqrt_n - 1)
    for i in range(first_defined):
        assert got[i] is None
    # For defined indices, recompute against the same windowed weighted sum
    weights = np.arange(1, sqrt_n + 1, dtype=float)
    w_sum = weights.sum()
    for i in range(first_defined, len(closes)):
        window_vals = diff[i - sqrt_n + 1 : i + 1]
        assert all(v is not None for v in window_vals)
        expected = float(np.dot(window_vals, weights) / w_sum)
        assert got[i] == pytest.approx(expected, rel=1e-9)


# ---------- VWMA ----------


def test_vwma_matches_reference():
    df = _frame(FIXTURE["closes"], FIXTURE["volumes"])
    got = _values(IndicatorSpec(type="vwma", params={"period": 3}), df)
    expected = FIXTURE["vwma_period_3"]
    for g, e in zip(got, expected):
        if e is None:
            assert g is None
        else:
            assert g == pytest.approx(e, rel=1e-9)


def test_vwma_requires_volume_column():
    df = _frame(FIXTURE["closes"])  # no volume
    with pytest.raises(VolumeRequiredError):
        compute(IndicatorSpec(type="vwma", params={"period": 3}), df)


def test_vwma_requires_non_null_volume():
    df = _frame(FIXTURE["closes"], [float("nan")] * len(FIXTURE["closes"]))
    with pytest.raises(VolumeRequiredError):
        compute(IndicatorSpec(type="vwma", params={"period": 3}), df)


# ---------- source resolution ----------


def test_source_hl2_averages_high_low():
    df = _frame([10.0, 12.0, 14.0, 16.0])
    got = _values(
        IndicatorSpec(type="sma", params={"period": 1, "source": "hl2"}), df
    )
    # hl2 = (close+0.5 + close-0.5)/2 = close for the synthetic frame
    assert got == [10.0, 12.0, 14.0, 16.0]


def test_unknown_source_errors():
    df = _frame([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        compute(
            IndicatorSpec(type="sma", params={"period": 2, "source": "bogus"}), df
        )
