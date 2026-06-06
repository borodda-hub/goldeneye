"""
Model registry. Runs all five models and returns individual + ensemble results.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from apps.api.services.models.factor_composite import predict as factor_predict
from apps.api.services.models.logreg_directional import predict as logreg_predict
from apps.api.services.models.moving_average_directional import ForecastResult
from apps.api.services.models.moving_average_directional import predict as ma_predict
from apps.api.services.models.prophet_trend import predict as prophet_predict
from apps.api.services.models.volatility_regime import predict as vol_predict


@dataclass
class ForecastContext:
    symbol: str
    closes: list[float]
    latest_storage: dict | None = None  # type: ignore[type-arg]
    latest_cot: dict | None = None  # type: ignore[type-arg]
    recent_events: list[dict] | None = field(default=None)  # type: ignore[type-arg]
    weather_anomaly: float | None = None


async def run_all(ctx: ForecastContext) -> list[ForecastResult]:
    """
    Run all five forecasting models and return the results.

    If ctx.closes has fewer than 55 values, return a single fallback ForecastResult
    indicating insufficient data.

    Args:
        ctx: ForecastContext with symbol, closes, and optional enrichment data.

    Returns:
        List of ForecastResult objects (4 models, or 1 fallback).
    """
    if len(ctx.closes) >= 55:
        results: list[ForecastResult] = [
            ma_predict(ctx.closes, "1d"),
            vol_predict(ctx.closes, "1d"),
            prophet_predict(ctx.closes, "1w"),
            factor_predict(ctx.closes, "1d", latest_storage=ctx.latest_storage, latest_cot=ctx.latest_cot),
            logreg_predict(ctx.closes, "1d"),
        ]
    else:
        results = [
            ForecastResult(
                model_name="moving_average_directional",
                horizon="1d",
                direction="neutral",
                confidence="low",
                expected_pct=None,
                range_low_pct=None,
                range_high_pct=None,
                vol_regime="normal",
                supporting=[],
                contradicting=[
                    {
                        "factor": "Insufficient price history",
                        "weight": 1.0,
                        "note": "Need at least 55 bars for full model suite.",
                    }
                ],
                inputs_used=["closes"],
            )
        ]
    return results
