"""Indicator-engine core: types, registry, and dispatch.

Each indicator family (moving_averages, channels, trend, …) registers its
compute functions at import time via `@register("type-key")`. The dispatcher
in `compute()` looks up the type, runs the function, and packs the resulting
pandas Series into an `IndicatorSeries` with NaN → None for chart-friendly
gap rendering.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel

PriceSource = Literal["close", "open", "high", "low", "hl2", "hlc3"]
_VALID_SOURCES: tuple[PriceSource, ...] = ("close", "open", "high", "low", "hl2", "hlc3")


class IndicatorSpec(BaseModel):
    type: str
    params: dict[str, Any]


class IndicatorPoint(BaseModel):
    t: datetime
    v: float | None


class IndicatorSeries(BaseModel):
    type: str
    params: dict[str, Any]
    points: list[IndicatorPoint]


class UnknownIndicatorError(ValueError):
    """compute() called with a type not present in the registry."""


class VolumeRequiredError(ValueError):
    """Indicator requires volume but the input has none."""


Computer = Callable[[pd.DataFrame, dict[str, Any]], pd.Series]
_REGISTRY: dict[str, Computer] = {}


def register(type_key: str) -> Callable[[Computer], Computer]:
    def deco(fn: Computer) -> Computer:
        _REGISTRY[type_key] = fn
        return fn

    return deco


def registered_types() -> list[str]:
    return sorted(_REGISTRY.keys())


def resolve_source(df: pd.DataFrame, source: PriceSource) -> pd.Series:
    if source == "close":
        return df["close"].astype(float)
    if source == "open":
        return df["open"].astype(float)
    if source == "high":
        return df["high"].astype(float)
    if source == "low":
        return df["low"].astype(float)
    if source == "hl2":
        return (df["high"].astype(float) + df["low"].astype(float)) / 2.0
    if source == "hlc3":
        return (
            df["high"].astype(float)
            + df["low"].astype(float)
            + df["close"].astype(float)
        ) / 3.0
    raise ValueError(f"unknown source: {source}")


def normalize_source(value: Any) -> PriceSource:
    src = value if value is not None else "close"
    if src not in _VALID_SOURCES:
        raise ValueError(f"unknown source: {src!r}; supported: {list(_VALID_SOURCES)}")
    return src


def compute(spec: IndicatorSpec, ohlcv: pd.DataFrame) -> IndicatorSeries:
    """Dispatch to the registered compute function for `spec.type`.

    `ohlcv` must have a datetime-like index and the columns the indicator
    needs (typically `close`; `volume` for volume-weighted variants).
    """
    fn = _REGISTRY.get(spec.type)
    if fn is None:
        raise UnknownIndicatorError(
            f"unknown indicator type {spec.type!r}; supported: {registered_types()}"
        )
    series = fn(ohlcv, spec.params)

    points: list[IndicatorPoint] = []
    for ts, raw in series.items():
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            v: float | None = None
        else:
            v = float(raw)
        points.append(IndicatorPoint(t=_to_datetime(ts), v=v))
    return IndicatorSeries(type=spec.type, params=spec.params, points=points)


def _to_datetime(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, pd.Timestamp):
        return datetime.fromisoformat(ts.isoformat())
    return datetime.fromisoformat(pd.Timestamp(ts).isoformat())
