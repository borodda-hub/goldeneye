"""Momentum / trend oscillators — RSI, MACD, Stochastic, ADX, ATR.

All render in a sub-pane below the price chart (their scales differ from price).
Multi-line indicators (MACD, Stochastic) return several named lines.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from apps.api.services.indicators.base import IndicatorResult, register


def _int(params: dict[str, Any], key: str, default: int) -> int:
    v = int(params.get(key, default))
    if v < 1:
        raise ValueError(f"{key} must be >= 1")
    return v


def _wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Wilder's Average True Range — shared by ATR/ADX/Keltner."""
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


@register("rsi")
def rsi(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = _int(params, "period", 14)
    close = df["close"].astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # When there are no losses in the window, RSI is 100 (rs → inf handles it,
    # but make the all-flat 0/0 case explicit).
    out = out.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return IndicatorResult(pane="sub", lines=[("rsi", out)])


@register("macd")
def macd(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    fast = _int(params, "fast", 12)
    slow = _int(params, "slow", 26)
    sig = _int(params, "signal", 9)
    close = df["close"].astype(float)
    macd_line = (
        close.ewm(span=fast, adjust=False).mean()
        - close.ewm(span=slow, adjust=False).mean()
    )
    signal = macd_line.ewm(span=sig, adjust=False).mean()
    hist = macd_line - signal
    return IndicatorResult(
        pane="sub",
        lines=[("macd", macd_line), ("signal", signal), ("hist", hist)],
    )


@register("stoch")
def stoch(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    k = _int(params, "k", 14)
    d = _int(params, "d", 3)
    smooth = _int(params, "smooth", 3)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    raw_k = 100.0 * (close - lowest) / (highest - lowest)
    k_line = raw_k.rolling(smooth).mean()
    d_line = k_line.rolling(d).mean()
    return IndicatorResult(pane="sub", lines=[("k", k_line), ("d", d_line)])


@register("adx")
def adx(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = _int(params, "period", 14)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0.0)).astype(float) * up
    minus_dm = ((down > up) & (down > 0.0)).astype(float) * down
    atr = _wilder_atr(df, period)
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr)
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_line = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return IndicatorResult(pane="sub", lines=[("adx", adx_line)])


@register("atr")
def atr(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = _int(params, "period", 14)
    return IndicatorResult(pane="sub", lines=[("line", _wilder_atr(df, period))])
