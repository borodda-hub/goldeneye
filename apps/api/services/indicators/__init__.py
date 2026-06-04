"""Chart-indicator compute layer (Phase 15).

Indicator implementations live in submodules grouped by family:
    moving_averages — SMA, EMA, WMA, HMA, DEMA, TEMA, VWMA (Phase 15)
    channels        — Bollinger, Keltner, Donchian (Phase 16)
    trend           — MACD, ADX/DMI, Parabolic SAR, SuperTrend, … (Phase 17)

The base module exposes `compute(spec, ohlcv_df) -> IndicatorSeries`, which
dispatches by `spec.type` through a registry. Each submodule registers its
indicators at import time so the dispatcher stays open to extension.

REST surface lives in `apps/api/routers/indicators.py` (Phase 15 step 15b).
"""
from __future__ import annotations

from apps.api.services.indicators import channels  # noqa: F401 — register
from apps.api.services.indicators import moving_averages  # noqa: F401 — register
from apps.api.services.indicators import oscillators  # noqa: F401 — register
from apps.api.services.indicators.base import (
    IndicatorLine,
    IndicatorPoint,
    IndicatorSeries,
    IndicatorSpec,
    UnknownIndicatorError,
    VolumeRequiredError,
    compute,
    registered_types,
)

__all__ = [
    "IndicatorLine",
    "IndicatorPoint",
    "IndicatorSeries",
    "IndicatorSpec",
    "UnknownIndicatorError",
    "VolumeRequiredError",
    "compute",
    "registered_types",
]
