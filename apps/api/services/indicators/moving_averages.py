"""Moving-average family (Phase 15).

Seven variants: SMA, EMA, WMA, HMA, DEMA, TEMA, VWMA. Each is a thin pandas/
numpy function registered with `base.compute`'s dispatcher.

Leading bars where the indicator is undefined (the first N-1 of an N-period
window, or the proportional warmup for stacked-EMA variants) are emitted as
NaN so the dispatcher converts them to `None` and charts render gaps rather
than misleading early values.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from apps.api.services.indicators.base import (
    VolumeRequiredError,
    normalize_source,
    register,
    resolve_source,
)


def _period(params: dict[str, Any]) -> int:
    period = int(params.get("period", 20))
    if period < 1:
        raise ValueError("period must be >= 1")
    return period


def _resolved(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    return resolve_source(df, normalize_source(params.get("source")))


def _wma_series(series: pd.Series, period: int) -> pd.Series:
    if period == 1:
        return series.astype(float).copy()
    weights = np.arange(1, period + 1, dtype=float)
    weight_sum = weights.sum()
    return series.rolling(window=period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / weight_sum), raw=True
    )


@register("sma")
def sma(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    period = _period(params)
    series = _resolved(df, params)
    return series.rolling(window=period, min_periods=period).mean()


@register("ema")
def ema(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    period = _period(params)
    series = _resolved(df, params)
    result = series.ewm(span=period, adjust=False).mean()
    if period > 1:
        result.iloc[: period - 1] = np.nan
    return result


@register("wma")
def wma(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    period = _period(params)
    series = _resolved(df, params)
    return _wma_series(series, period)


@register("hma")
def hma(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    """Hull MA: WMA(2*WMA(period/2) - WMA(period), sqrt(period))."""
    period = _period(params)
    series = _resolved(df, params)
    half = max(1, period // 2)
    sqrt_n = max(1, int(round(np.sqrt(period))))
    diff = 2 * _wma_series(series, half) - _wma_series(series, period)
    return _wma_series(diff, sqrt_n)


@register("dema")
def dema(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    """DEMA = 2*EMA - EMA(EMA)."""
    period = _period(params)
    series = _resolved(df, params)
    e1 = series.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period, adjust=False).mean()
    result = 2 * e1 - e2
    if period > 1:
        warmup = min(len(result), 2 * (period - 1))
        result.iloc[:warmup] = np.nan
    return result


@register("tema")
def tema(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    """TEMA = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))."""
    period = _period(params)
    series = _resolved(df, params)
    e1 = series.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period, adjust=False).mean()
    e3 = e2.ewm(span=period, adjust=False).mean()
    result = 3 * e1 - 3 * e2 + e3
    if period > 1:
        warmup = min(len(result), 3 * (period - 1))
        result.iloc[:warmup] = np.nan
    return result


@register("vwma")
def vwma(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    """Volume-weighted MA. Errors if volume is missing or entirely null."""
    period = _period(params)
    if "volume" not in df.columns or df["volume"].isna().all():
        raise VolumeRequiredError("VWMA requires a non-null `volume` column.")
    prices = _resolved(df, params)
    volumes = df["volume"].astype(float)
    pv = prices * volumes
    num = pv.rolling(window=period, min_periods=period).sum()
    den = volumes.rolling(window=period, min_periods=period).sum()
    return num / den
