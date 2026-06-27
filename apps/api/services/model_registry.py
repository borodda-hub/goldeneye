"""
Model registry. Runs the four directional voter models and returns individual
results. The volatility regime is computed once as shared *context* (stamped onto
every result and consumed by the ensemble) rather than casting its own weak
directional vote — see docs/BUILD_ROADMAP.md §26b.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from apps.api.services.asset_config import AssetClassConfig, config_for
from apps.api.services.models.factor_composite import predict as factor_predict
from apps.api.services.models.holt_trend import predict as holt_predict
from apps.api.services.models.logreg_directional import predict as logreg_predict
from apps.api.services.models.moving_average_directional import ForecastResult
from apps.api.services.models.moving_average_directional import predict as ma_predict
from apps.api.services.models.volatility_regime import classify as classify_regime


@dataclass
class ForecastContext:
    symbol: str
    closes: list[float]
    latest_storage: dict | None = None  # type: ignore[type-arg]
    latest_cot: dict | None = None  # type: ignore[type-arg]
    recent_events: list[dict] | None = field(default=None)  # type: ignore[type-arg]
    weather_anomaly: float | None = None
    # B5: per-asset-class engine config. Defaults to "commodity" so every existing
    # caller stays byte-identical; instrument-aware callers pass the real class.
    asset_class: str = "commodity"
    cfg: AssetClassConfig = field(init=False)

    def __post_init__(self) -> None:
        self.cfg = config_for(self.asset_class)


async def run_all(ctx: ForecastContext) -> list[ForecastResult]:
    """
    Run the four directional voter models and return the results.

    The volatility regime is classified once and stamped onto every result as
    shared context (it no longer casts its own directional vote). If ctx.closes
    has fewer than 55 values, return a single fallback ForecastResult indicating
    insufficient data.

    Args:
        ctx: ForecastContext with symbol, closes, and optional enrichment data.

    Returns:
        List of ForecastResult objects (4 voters, or 1 fallback).
    """
    if len(ctx.closes) >= 55:
        regime = classify_regime(ctx.closes, ctx.cfg)
        results: list[ForecastResult] = [
            ma_predict(ctx.closes, "1d", ctx.cfg),
            holt_predict(ctx.closes, "1d", ctx.cfg),
            factor_predict(
                ctx.closes,
                "1d",
                latest_storage=ctx.latest_storage,
                latest_cot=ctx.latest_cot,
                cfg=ctx.cfg,
            ),
            logreg_predict(ctx.closes, "1d", cfg=ctx.cfg),
        ]
        # vol_regime as shared context: stamp the single classification onto each
        # voter so the ensemble + diagnostics read one consistent regime.
        for r in results:
            r.vol_regime = regime
        return results
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
