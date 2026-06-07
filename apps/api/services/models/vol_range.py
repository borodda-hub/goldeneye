"""Volatility & range forecast — Phase 30a.

The platform's first calibrated-*by-construction* forecaster. Phase 26 established that
price *direction* is near-random (no out-of-sample confidence gradient at any horizon).
Volatility is the opposite: a walk-forward probe found EWMA-vol bands give ~80% interval
coverage on NG with zero tuning. So this model forecasts the expected price **range**
over a horizon — it makes **no directional claim**.

Mechanism: a RiskMetrics EWMA (λ=0.94) estimate of daily log-return volatility, scaled
to the horizon by √h, turned into symmetric ±z·σ·√h bands around the current price.
Look-ahead-safe: it only ever consumes the closes handed to it.

Both bands are calibrated by **empirical quantiles of past realized standardized moves**
(Phase 30c): the multiplier for a level is the walk-forward quantile of ``|cum_h_return /
(σ·√h)|``, not a fixed normal z. Real returns are fat-tailed, so the 95% multiplier runs
above 1.96 and the 95% band reaches its honest coverage instead of running light (the
normal-z version under-covered ~92–94% on real data). The estimate uses only residuals
realized in the past, with a normal-z fallback until ~``_MIN_TAIL`` residuals exist.
``walk_forward_coverage`` is the honest track-record readout (and the locked calibration
test): it never asserts the band is right, it *measures* how often it actually contained
the move.

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
# Two-sided normal z for each confidence level (avoids a scipy dependency). Used as the
# warm-up fallback before there are enough realized residuals to estimate fat tails (30c).
_Z = {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.9600}
# Below this many realized standardized residuals, fall back to the normal z (an empirical
# tail quantile estimated from a handful of points is noise). ~40 ≈ the smallest sample
# whose 95th percentile is meaningful.
_MIN_TAIL = 40


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


def _wf_sigma(rets: np.ndarray) -> np.ndarray:
    """Walk-forward EWMA daily vol: ``sigma[t]`` uses only ``rets[:t+1]`` (look-ahead-safe)."""
    seed = rets[:_WARMUP]
    v = float(np.var(seed)) if seed.size else 0.0
    sigma = np.empty(rets.size)
    for t in range(rets.size):
        v = _LAMBDA * v + (1.0 - _LAMBDA) * float(rets[t]) ** 2
        sigma[t] = np.sqrt(v)
    return sigma


def _standardized_abs(rets: np.ndarray, sigma: np.ndarray, h: int) -> tuple[np.ndarray, np.ndarray]:
    """|standardized h-day moves| and the index by which each is realized (30c fat tails).

    For each decision point ``s`` (``s ≥ _WARMUP``), the realized cumulative h-day move
    ``Σ rets[s+1 : s+1+h]`` is divided by ``sigma[s]·√h`` — i.e. measured in walk-forward
    sigma-units (``sigma[s]`` uses only ``rets[:s+1]``). The empirical quantiles of these
    absolute values are the band multipliers: under normality the 95th percentile is 1.96,
    but real returns are fat-tailed so it runs higher — which is exactly the 95%-band
    under-coverage 30c fixes. Returns ``(abs_u, realized_by)`` where ``realized_by[i] = s+h``
    is the first index at which residual ``i`` is fully known (so the walk-forward coverage
    loop can use only residuals realized strictly before its decision point — no look-ahead).
    """
    n = rets.size
    sh = float(np.sqrt(h))
    vals: list[float] = []
    realized_by: list[int] = []
    for s in range(_WARMUP, n - h):
        denom = sigma[s] * sh
        if denom <= 0.0:
            continue
        cum = float(rets[s + 1 : s + 1 + h].sum())
        vals.append(abs(cum / denom))
        realized_by.append(s + h)
    return np.asarray(vals), np.asarray(realized_by, dtype=int)


def _multiplier(abs_u: np.ndarray, level: float) -> float:
    """Band multiplier for a confidence level: the empirical ``level``-quantile of the
    realized |standardized| moves, or the normal z while the sample is too thin to trust."""
    if abs_u.size >= _MIN_TAIL:
        return float(np.quantile(abs_u, level))
    return _Z[level]


def predict(closes: list[float], horizon: str = "1w") -> RangeForecast | None:
    """Forecast the symmetric price range over `horizon`. None on thin/bad input."""
    h = _HORIZON_TDAYS.get(horizon, 5)
    c = np.asarray(closes, dtype=float)
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return None
    rets = np.diff(np.log(c))
    sigma = _wf_sigma(rets)
    sig_d = float(sigma[-1])  # current EWMA daily vol = the final walk-forward step
    sig_h = sig_d * float(np.sqrt(h))
    # Fat-tailed band multipliers: the empirical quantiles of past realized standardized
    # moves (full history = look-ahead-safe at serve time), falling back to the normal z
    # until there are enough residuals. Real returns are fat-tailed, so m95 > 1.96 → the
    # 95% band widens to its honest coverage (30c).
    abs_u, _ = _standardized_abs(rets, sigma, h)
    m80 = _multiplier(abs_u, 0.80)
    m95 = _multiplier(abs_u, 0.95)
    empirical = abs_u.size >= _MIN_TAIL
    return RangeForecast(
        horizon=horizon,
        sigma_daily=round(sig_d, 6),
        sigma_horizon=round(sig_h, 6),
        band80_low_pct=round(-m80 * sig_h, 5),
        band80_high_pct=round(m80 * sig_h, 5),
        band95_low_pct=round(-m95 * sig_h, 5),
        band95_high_pct=round(m95 * sig_h, 5),
        method="ewma+empirical-tails" if empirical else "ewma",
        note=(
            f"EWMA(λ={_LAMBDA}) daily vol {sig_d * 100:.2f}% scaled to {horizon} "
            f"(±q·σ·√h, q from {'empirical fat-tail' if empirical else 'normal'} quantiles; "
            f"95%×{m95:.2f}). Symmetric range — no directional claim."
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
    # Fat-tail multipliers estimated walk-forward: at each decision t the band uses only
    # standardized residuals already *realized* by t (``realized_by <= t``), so no future
    # tail information leaks into the band. Thin early windows fall back to the normal z.
    abs_u, realized_by = _standardized_abs(rets, sigma, h)
    counts = {lv: [0, 0] for lv in levels}
    sh = float(np.sqrt(h))
    for t in range(_WARMUP, n - h):
        cum = float(rets[t + 1 : t + 1 + h].sum())
        band = sigma[t] * sh
        past = abs_u[realized_by <= t] if abs_u.size else abs_u
        for lv in levels:
            counts[lv][1] += 1
            if abs(cum) <= _multiplier(past, lv) * band:
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
