"""Volatility channels — Bollinger, Keltner, Donchian.

All overlay the price pane as a 3-line band (upper / mid / lower).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from apps.api.services.indicators.base import IndicatorResult, register
from apps.api.services.indicators.oscillators import _wilder_atr


def _band(upper: pd.Series, mid: pd.Series, lower: pd.Series) -> IndicatorResult:
    return IndicatorResult(
        pane="price", lines=[("upper", upper), ("mid", mid), ("lower", lower)]
    )


@register("bb")
def bollinger(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = int(params.get("period", 20))
    k = float(params.get("stddev", 2.0))
    close = df["close"].astype(float)
    mid = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    return _band(mid + k * std, mid, mid - k * std)


@register("kc")
def keltner(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = int(params.get("period", 20))
    mult = float(params.get("mult", 2.0))
    mid = df["close"].astype(float).ewm(span=period, adjust=False).mean()
    atr = _wilder_atr(df, period)
    return _band(mid + mult * atr, mid, mid - mult * atr)


@register("dc")
def donchian(df: pd.DataFrame, params: dict[str, Any]) -> IndicatorResult:
    period = int(params.get("period", 20))
    upper = df["high"].astype(float).rolling(period).max()
    lower = df["low"].astype(float).rolling(period).min()
    return _band(upper, (upper + lower) / 2.0, lower)
