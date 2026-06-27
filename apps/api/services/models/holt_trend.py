"""Holt linear-trend model — the platform's always-on *statistical time-series*
forecaster (Phase 26b).

This fills the "statistical" slot that Prophet only filled when it happened to be
installed. It runs Holt's linear (double-exponential smoothing) method in pure
numpy: a level and a trend component, projected ``h`` steps ahead. The smoothing
parameters (alpha, beta) are chosen by a small deterministic grid search that
minimises one-step-ahead in-sample SSE — so the fit adapts to the series instead
of using magic constants, while staying dependency-free and reproducible.

Look-ahead-safe by construction: it only ever consumes the closes it is handed,
and in the backtest that window is strictly ``< as_of``. The direction comes from
the projected move; confidence comes from the trend's signal-to-noise ratio
(trend per step vs the residual scale), not from how much we *want* to believe it.
The expected move and range are reported with an explicit "smoothing projection,
not a guarantee" framing.
"""

from __future__ import annotations

import numpy as np

from apps.api.services.asset_config import DEFAULT, AssetClassConfig

# Horizon → trading-day projection and the (alpha, beta) grid. (min_closes,
# neutral_band, and the SNR confidence cutoffs are per-asset-class — see cfg.holt.)
_HORIZON_TDAYS = {"1d": 1, "1w": 5, "1m": 21}
_MIN_CLOSES = 30  # commodity default; cfg.holt.min_closes overrides per class
_ALPHAS = (0.1, 0.3, 0.5, 0.7, 0.9)
_BETAS = (0.05, 0.1, 0.2, 0.4)


def _insufficient(horizon: str) -> "ForecastResult":  # noqa: F821
    from apps.api.services.models.moving_average_directional import ForecastResult

    return ForecastResult(
        model_name="holt_trend",
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
                "factor": "Insufficient history to smooth",
                "weight": 1.0,
                "note": f"Need ~{_MIN_CLOSES} closes to fit a stable trend; returning neutral.",
            }
        ],
        inputs_used=["closes"],
    )


def _holt(y: np.ndarray, alpha: float, beta: float) -> tuple[np.ndarray, float, float]:
    """Run Holt's linear method over y. Returns (one-step fitted values aligned to
    y[1:], final level, final trend). Fitted[i] is the forecast of y[i+1] made at i.
    """
    level = y[0]
    trend = y[1] - y[0]
    fitted = np.empty(y.size - 1)
    for i in range(1, y.size):
        fitted[i - 1] = level + trend  # one-step-ahead forecast of y[i]
        prev_level = level
        level = alpha * y[i] + (1.0 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * trend
    return fitted, float(level), float(trend)


def _best_fit(y: np.ndarray) -> tuple[float, float, np.ndarray, float, float]:
    """Grid-search (alpha, beta) minimising one-step SSE. Deterministic."""
    best: tuple[float, float, np.ndarray, float, float] | None = None
    best_sse = np.inf
    actual = y[1:]
    for alpha in _ALPHAS:
        for beta in _BETAS:
            fitted, level, trend = _holt(y, alpha, beta)
            sse = float(np.sum((actual - fitted) ** 2))
            if sse < best_sse:
                best_sse = sse
                best = (alpha, beta, fitted, level, trend)
    assert best is not None  # _ALPHAS/_BETAS are non-empty
    return best


def predict(
    closes: list[float], horizon: str = "1d", cfg: AssetClassConfig | None = None
) -> "ForecastResult":  # noqa: F821
    from apps.api.services.models.moving_average_directional import ForecastResult

    cfg = cfg if cfg is not None else DEFAULT
    h = _HORIZON_TDAYS.get(horizon, 1)
    y = np.asarray(closes, dtype=float)
    if y.size < cfg.holt.min_closes or np.any(y <= 0):
        return _insufficient(horizon)

    alpha, beta, fitted, level, trend = _best_fit(y)
    last = float(y[-1])

    # Projection h steps ahead and its implied pct move off the last close.
    projected = level + h * trend
    expected_pct = projected / last - 1.0 if last else 0.0

    # Residual scale of the one-step fit → range + signal-to-noise for confidence.
    resid = y[1:] - fitted
    resid_std = float(np.std(resid))
    resid_pct = resid_std / last if last else 0.0
    # Scale the residual band to the horizon (random-walk-style sqrt(h) widening).
    band = resid_pct * float(np.sqrt(h))

    if expected_pct > cfg.holt.neutral_band:
        direction = "bullish"
    elif expected_pct < -cfg.holt.neutral_band:
        direction = "bearish"
    else:
        direction = "neutral"

    # Signal-to-noise: projected move vs the noise band. Strong, clean trends get
    # high confidence; a move swamped by residual noise stays low.
    snr = abs(expected_pct) / band if band > 0 else 0.0
    if direction == "neutral":
        confidence = "low"
    elif snr >= cfg.holt.snr_high:
        confidence = "high"
    elif snr >= cfg.holt.snr_medium:
        confidence = "medium"
    else:
        confidence = "low"

    trend_per_day_pct = trend / last if last else 0.0
    supporting = [
        {
            "factor": "Holt linear trend",
            "weight": round(min(snr, 1.0), 3),
            "note": (
                f"Smoothed trend of {trend_per_day_pct * 100:+.3f}%/day "
                f"(alpha={alpha}, beta={beta}) projects {direction} over {horizon}."
            ),
        }
    ]
    contradicting = [
        {
            "factor": "Smoothing projection, not a guarantee",
            "weight": round(min(band, 1.0), 3),
            "note": (
                f"One-step residual scale is {resid_pct * 100:.2f}% of price; the "
                "projection extrapolates the recent trend and ignores regime shifts."
            ),
        }
    ]

    return ForecastResult(
        model_name="holt_trend",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=round(expected_pct, 5),
        range_low_pct=round(expected_pct - band, 5),
        range_high_pct=round(expected_pct + band, 5),
        vol_regime=None,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=["closes"],
    )
