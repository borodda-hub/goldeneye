"""Volatility & range forecast — Phase 30a.

The platform's first calibrated-*by-construction* forecaster. Phase 26 established that
price *direction* is near-random (no out-of-sample confidence gradient at any horizon).
Volatility is the opposite: a walk-forward probe found EWMA-vol bands give ~80% interval
coverage on NG with zero tuning. So this model forecasts the expected price **range**
over a horizon — it makes **no directional claim**.

Mechanism: a RiskMetrics EWMA (λ=0.94) estimate of daily log-return volatility, scaled
to the horizon by √h, turned into symmetric ±z·σ·√h bands around the current price.
Look-ahead-safe: it only ever consumes the closes handed to it.

The **80% band is the calibrated surface** (its walk-forward coverage is the gate). The
95% band is reported but runs light because returns are fatter-tailed than normal — a
Student-t / empirical-quantile fix is Phase 30c. ``walk_forward_coverage`` is the honest
track-record readout (and the locked calibration test): it never asserts the band is
right, it *measures* how often it actually contained the move.

``forecast_vol_correlation`` is the second honest readout: the walk-forward correlation
between the vol *forecast* and realized forward vol. It is the evidence the forecaster
carries genuine information (≈0.3–0.4 on the seeded regime-switching series, ≈0 on
constant-vol data — no spurious signal). The point-forecast vol *level* is NOT reliable
out-of-sample (R² is negative): use the band width, not the central σ as a precise
prediction. Honest caveat on both readouts: walk-forward windows overlap, so estimates
are stable but their significance is overstated relative to ``n_eff`` independent windows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_LAMBDA = 0.94  # RiskMetrics EWMA decay
_WARMUP = 25
_MIN_CLOSES = 30
_HORIZON_TDAYS = {"1d": 1, "1w": 5, "1m": 21}
# Two-sided normal z for each confidence level (avoids a scipy dependency).
_Z = {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.9600}


@dataclass
class RangeForecast:
    horizon: str
    sigma_daily: float  # EWMA daily log-return vol
    sigma_horizon: float  # scaled to the horizon (σ·√h)
    band80_low_pct: float
    band80_high_pct: float
    band95_low_pct: float
    band95_high_pct: float
    method: str
    note: str


def _ewma_sigma(rets: np.ndarray) -> float:
    """Final EWMA daily vol over all provided returns (look-ahead-safe)."""
    seed = rets[:_WARMUP] if rets.size >= _WARMUP else rets
    v = float(np.var(seed)) if seed.size else 0.0
    for r in rets:
        v = _LAMBDA * v + (1.0 - _LAMBDA) * float(r) ** 2
    return float(np.sqrt(v))


def _wf_sigma(rets: np.ndarray) -> np.ndarray:
    """Walk-forward EWMA daily vol: ``sigma[t]`` uses only ``rets[:t+1]`` (look-ahead-safe)."""
    seed = rets[:_WARMUP]
    v = float(np.var(seed)) if seed.size else 0.0
    sigma = np.empty(rets.size)
    for t in range(rets.size):
        v = _LAMBDA * v + (1.0 - _LAMBDA) * float(rets[t]) ** 2
        sigma[t] = np.sqrt(v)
    return sigma


def predict(closes: list[float], horizon: str = "1w") -> RangeForecast | None:
    """Forecast the symmetric price range over `horizon`. None on thin/bad input."""
    h = _HORIZON_TDAYS.get(horizon, 5)
    c = np.asarray(closes, dtype=float)
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return None
    rets = np.diff(np.log(c))
    sig_d = _ewma_sigma(rets)
    sig_h = sig_d * float(np.sqrt(h))
    return RangeForecast(
        horizon=horizon,
        sigma_daily=round(sig_d, 6),
        sigma_horizon=round(sig_h, 6),
        band80_low_pct=round(-_Z[0.80] * sig_h, 5),
        band80_high_pct=round(_Z[0.80] * sig_h, 5),
        band95_low_pct=round(-_Z[0.95] * sig_h, 5),
        band95_high_pct=round(_Z[0.95] * sig_h, 5),
        method="ewma",
        note=(
            f"EWMA(λ={_LAMBDA}) daily vol {sig_d * 100:.2f}% scaled to {horizon} "
            "(±z·σ·√h). Symmetric range — no directional claim."
        ),
    )


def walk_forward_coverage(
    closes: list[float],
    horizon: str = "1w",
    levels: tuple[float, ...] = (0.80, 0.95),
) -> dict[str, float | None]:
    """Realized interval coverage of the EWMA bands over the series, walk-forward.

    The calibration gate + honest readout: at each t the band uses only ``closes[:t+1]``;
    we then check whether the realized cumulative h-day return falls inside ±z·σ·√h.
    Coverage is measured over *every* step (overlapping windows) for a stable estimate;
    ``n_eff`` reports the count of *independent* (non-overlapping) h-day windows, so the
    precision of the estimate isn't over-read — consecutive overlapping windows share
    h−1 returns and are not independent trials.
    Returns ``{"cov80": 0.79, "cov95": 0.90, "n_eff": 140}`` (cov None per level if too
    little data).
    """
    h = _HORIZON_TDAYS.get(horizon, 5)
    c = np.asarray(closes, dtype=float)
    out: dict[str, float | None] = {f"cov{int(lv * 100)}": None for lv in levels}
    out["n_eff"] = 0
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return out
    rets = np.diff(np.log(c))
    n = rets.size
    if n <= _WARMUP + h:
        return out

    sigma = _wf_sigma(rets)
    counts = {lv: [0, 0] for lv in levels}
    for t in range(_WARMUP, n - h):
        cum = float(rets[t + 1 : t + 1 + h].sum())
        band = sigma[t] * float(np.sqrt(h))
        for lv in levels:
            counts[lv][1] += 1
            if abs(cum) <= _Z[lv] * band:
                counts[lv][0] += 1
    res: dict[str, float | None] = {
        f"cov{int(lv * 100)}": (counts[lv][0] / counts[lv][1] if counts[lv][1] else None)
        for lv in levels
    }
    res["n_eff"] = len(range(_WARMUP, n - h, h))  # independent (non-overlapping) windows
    return res


def forecast_vol_correlation(closes: list[float], horizon: str = "1w") -> float | None:
    """Walk-forward correlation between the vol *forecast* and realized forward vol.

    At each t the forecast σ uses only ``closes[:t+1]``; we correlate it against the
    realized daily volatility over the *next* h days (RMS of the forward returns). A
    positive value is the evidence the forecaster carries genuine information about
    forthcoming volatility — the platform's one calibrated edge (Phase 30). It sits near
    zero on constant-vol data (no spurious signal) and ≈0.3–0.4 on the regime-switching
    seeded series. Returns None on thin input.

    Honest caveat: walk-forward windows overlap, so this is a stable point estimate but
    its significance (SE) is overstated relative to the independent-window count — read
    the magnitude, not a t-stat.
    """
    h = _HORIZON_TDAYS.get(horizon, 5)
    c = np.asarray(closes, dtype=float)
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return None
    rets = np.diff(np.log(c))
    n = rets.size
    if n <= _WARMUP + h:
        return None
    sigma = _wf_sigma(rets)
    fc = sigma[_WARMUP : n - h]
    rz = np.array(
        [float(np.sqrt(np.mean(rets[t + 1 : t + 1 + h] ** 2))) for t in range(_WARMUP, n - h)]
    )
    if fc.size < 3 or float(np.std(fc)) == 0.0 or float(np.std(rz)) == 0.0:
        return None
    return round(float(np.corrcoef(fc, rz)[0, 1]), 4)
