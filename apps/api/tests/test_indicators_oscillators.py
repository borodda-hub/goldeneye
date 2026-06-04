"""Phase 23 — oscillators (RSI/MACD/Stochastic/ADX/ATR) + channels (BB/KC/DC)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from apps.api.routers.indicators import _parse_spec
from apps.api.services.indicators import compute
from apps.api.services.indicators.base import IndicatorSpec


def _df(n: int = 80) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + np.abs(rng.normal(0, 0.5, n)),
            "low": close - np.abs(rng.normal(0, 0.5, n)),
            "close": close,
            "volume": 1000 + rng.integers(0, 500, n),
        },
        index=idx,
    )


def _roles(type_: str, params: dict) -> tuple[str, list[str]]:
    s = compute(IndicatorSpec(type=type_, params=params), _df())
    return s.pane, [line.role for line in s.lines]


def test_rsi_is_sub_pane_single_line_in_0_100():
    s = compute(IndicatorSpec(type="rsi", params={"period": 14}), _df())
    assert s.pane == "sub"
    assert [line.role for line in s.lines] == ["rsi"]
    vals = [p.v for p in s.lines[0].points if p.v is not None]
    assert vals and all(0.0 <= v <= 100.0 for v in vals)


def test_macd_three_lines_sub_pane():
    pane, roles = _roles("macd", {"fast": 12, "slow": 26, "signal": 9})
    assert pane == "sub"
    assert roles == ["macd", "signal", "hist"]


def test_stoch_two_lines():
    pane, roles = _roles("stoch", {"k": 14, "d": 3, "smooth": 3})
    assert pane == "sub"
    assert roles == ["k", "d"]


def test_bollinger_band_ordering_on_price_pane():
    s = compute(IndicatorSpec(type="bb", params={"period": 20, "stddev": 2}), _df())
    assert s.pane == "price"
    assert [line.role for line in s.lines] == ["upper", "mid", "lower"]
    upper = [p.v for p in s.lines[0].points]
    mid = [p.v for p in s.lines[1].points]
    lower = [p.v for p in s.lines[2].points]
    for u, m, lo in zip(upper, mid, lower):
        if u is not None and m is not None and lo is not None:
            assert u >= m >= lo


@pytest.mark.parametrize("t", ["adx", "atr", "kc", "dc"])
def test_remaining_indicators_compute(t):
    params = {"period": 14} if t in ("adx", "atr", "dc") else {"period": 20, "mult": 2}
    s = compute(IndicatorSpec(type=t, params=params), _df())
    assert s.lines and s.pane in ("price", "sub")


# ── Parser ─────────────────────────────────────────────────────────────────


def test_parser_macd_positional_params():
    specs = _parse_spec("macd:12:26:9")
    assert specs[0].type == "macd"
    assert specs[0].params == {"fast": 12, "slow": 26, "signal": 9}


def test_parser_bb_with_float_stddev():
    specs = _parse_spec("bb:20:2")
    assert specs[0].params["period"] == 20
    assert specs[0].params["stddev"] == 2.0


def test_parser_ma_still_works():
    specs = _parse_spec("ema:21,sma:50:hl2")
    assert specs[0].type == "ema" and specs[0].params == {"period": 21, "source": "close"}
    assert specs[1].params == {"period": 50, "source": "hl2"}


def test_parser_defaults_when_params_omitted():
    specs = _parse_spec("macd")
    assert specs[0].params == {"fast": 12, "slow": 26, "signal": 9}
