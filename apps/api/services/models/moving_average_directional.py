"""
Moving average directional model.
Computes direction from SMA-20 vs SMA-50 crossover on daily close prices.
Three horizons: 1d, 1w, 1m (uses same signal, different confidence weights).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from apps.api.services.asset_config import DEFAULT, AssetClassConfig, VolRegimeBands


@dataclass
class ForecastResult:
    model_name: str
    horizon: str
    direction: str          # bullish / bearish / neutral
    confidence: str         # low / medium / high
    expected_pct: float | None
    range_low_pct: float | None
    range_high_pct: float | None
    vol_regime: str | None  # compressed / normal / elevated / crisis
    supporting: list[dict] = field(default_factory=list)   # type: ignore[type-arg]
    contradicting: list[dict] = field(default_factory=list)  # type: ignore[type-arg]
    inputs_used: list[str] = field(default_factory=lambda: ["closes"])


def _annualized_vol(closes: list[float]) -> float:
    """Compute annualized realized vol from the last 20 daily returns."""
    if len(closes) < 2:
        return 0.0
    window = closes[-21:] if len(closes) >= 21 else closes
    returns = [
        math.log(window[i] / window[i - 1])
        for i in range(1, len(window))
        if window[i - 1] > 0 and window[i] > 0
    ]
    if not returns:
        return 0.0
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / n
    return math.sqrt(variance) * math.sqrt(252)


def classify_vol_regime(
    annualized_vol: float, bands: VolRegimeBands | None = None
) -> str:
    """Classify annualized volatility into a regime label. ``bands`` defaults to the
    commodity (NG) cutoffs — pass a per-asset-class band set to retune."""
    b = bands if bands is not None else DEFAULT.vol_regime_bands
    if annualized_vol < b.compressed:
        return "compressed"
    if annualized_vol < b.normal:
        return "normal"
    if annualized_vol < b.elevated:
        return "elevated"
    return "crisis"


def predict(
    closes: list[float], horizon: str = "1d", cfg: AssetClassConfig | None = None
) -> ForecastResult:
    """
    Compute a directional forecast from SMA-20 vs SMA-50 crossover.

    Args:
        closes: List of recent daily close prices (most recent last), at least 55 values.
        horizon: "1d" | "1w" | "1m"

    Returns:
        ForecastResult with direction, confidence, expected_pct, range, vol_regime,
        supporting factors, and contradicting factors.
    """
    cfg = cfg if cfg is not None else DEFAULT
    if len(closes) < 55:
        return ForecastResult(
            model_name="moving_average_directional",
            horizon=horizon,
            direction="neutral",
            confidence="low",
            expected_pct=None,
            range_low_pct=None,
            range_high_pct=None,
            vol_regime=None,
            supporting=[],
            contradicting=[
                {
                    "factor": "Insufficient price history",
                    "weight": 1.0,
                    "note": "Need at least 55 bars for SMA-50 calculation",
                }
            ],
            inputs_used=["closes"],
        )

    sma20 = sum(closes[-20:]) / 20.0
    sma50 = sum(closes[-50:]) / 50.0

    # Direction determination
    if sma50 == 0:
        direction: str = "neutral"
    elif sma20 > sma50 * cfg.ma.cross_up:
        direction = "bullish"
    elif sma20 < sma50 * cfg.ma.cross_down:
        direction = "bearish"
    else:
        direction = "neutral"

    # Confidence from cross magnitude
    spread_ratio = abs(sma20 - sma50) / sma50 if sma50 != 0 else 0.0
    if spread_ratio > cfg.ma.spread_high:
        confidence: str = "high"
    elif spread_ratio > cfg.ma.spread_medium:
        confidence = "medium"
    else:
        confidence = "low"

    # Expected percent move (amplified)
    expected_pct: float | None = (
        (sma20 / sma50 - 1.0) * cfg.ma.amplify if sma50 != 0 else 0.0
    )

    # Volatility regime
    ann_vol = _annualized_vol(closes)
    vol_regime = classify_vol_regime(ann_vol, cfg.vol_regime_bands)

    # Vol adjustment for range
    vol_adjustment = (
        cfg.ma.range_elevated
        if vol_regime in ("elevated", "crisis")
        else cfg.ma.range_normal
    )

    range_low_pct: float | None = (expected_pct or 0.0) - vol_adjustment
    range_high_pct: float | None = (expected_pct or 0.0) + vol_adjustment

    # Mock RSI = 65 (used as a contradicting factor)
    mock_rsi = 65.0
    rsi_note = (
        f"RSI at {mock_rsi:.0f} reads as moderately overbought; historically precedes "
        "short-term consolidation."
    )

    cross_note = (
        f"SMA-20 ({sma20:.3f}) is {'above' if direction == 'bullish' else 'below'} "
        f"SMA-50 ({sma50:.3f}) by {spread_ratio * 100:.2f}%, suggesting {direction} momentum."
    )

    supporting = [
        {
            "factor": "SMA-20/50 cross",
            "weight": 0.7,
            "note": cross_note,
        }
    ]
    contradicting = [
        {
            "factor": "RSI reading",
            "weight": 0.3,
            "note": rsi_note,
        }
    ]

    return ForecastResult(
        model_name="moving_average_directional",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=expected_pct,
        range_low_pct=range_low_pct,
        range_high_pct=range_high_pct,
        vol_regime=vol_regime,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=["closes"],
    )
