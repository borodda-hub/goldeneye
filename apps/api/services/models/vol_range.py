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
# HAR-RV (Corsi 2009) realized-variance components, in trading days.
_HAR_W = 5  # weekly component
_HAR_M = 22  # monthly component
# Minimum look-ahead-safe (features, target) pairs before HAR replaces the EWMA fallback.
# 4 free params → a few dozen rows is the floor for a non-degenerate OLS fit.
_HAR_MIN_TRAIN = 60
# Variance floor for log-HAR so ``log(RV)`` is finite on (near-)zero-return days. 1e-6 ≈ a
# 0.1%/day move²; it only bites on genuinely tiny moves and has low leverage (daily component).
_HAR_FLOOR = 1e-6
# Refit cadence for the HAR OLS (Phase 30d perf pass). The original refit-every-step cost an
# O(n) OLS solve per decision point; the coefficients barely move between adjacent days, so we
# refit every ``_HAR_REFIT`` steps and reuse the (strictly-older-data) beta in between. Keyed to
# the ABSOLUTE index (``d_start + k·_HAR_REFIT``), so the forecast at any d stays prefix-invariant
# (a truncated series hits the same refit points → identical beta → look-ahead-safe). Weekly (5)
# is a conservative cadence: ~5× fewer solves with the real-OOS skill over EWMA preserved
# (re-validated via seeds/validate_estimator_30b.py).
_HAR_REFIT = 5


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


def _har_features(rv: np.ndarray) -> np.ndarray:
    """HAR design rows ``[1, RV_d, RV_w, RV_m]`` from a realized-variance proxy ``rv``.

    ``RV_d`` = today's 1-day realized variance; ``RV_w`` / ``RV_m`` = trailing 5- / 22-day
    means (Corsi's daily/weekly/monthly cascade). Row ``t`` uses only ``rv[:t+1]``
    (look-ahead-safe); rows before ``_HAR_M-1`` are NaN (insufficient trailing history).
    """
    n = rv.size
    x = np.full((n, 4), np.nan)
    csum = np.concatenate(([0.0], np.cumsum(rv)))  # csum[i] = sum(rv[:i])
    for t in range(_HAR_M - 1, n):
        x[t, 0] = 1.0
        x[t, 1] = rv[t]
        x[t, 2] = (csum[t + 1] - csum[t + 1 - _HAR_W]) / _HAR_W
        x[t, 3] = (csum[t + 1] - csum[t + 1 - _HAR_M]) / _HAR_M
    return x


def _har_rv_sigma(rets: np.ndarray, h: int, *, log: bool = False) -> np.ndarray:
    """Walk-forward HAR-RV (Corsi 2009) forecast of forward h-day average daily vol.

    ``sigma[t]`` is the forecast *made at t* — using only ``rets[:t+1]`` — of the average
    daily volatility over the next ``h`` days. It is fit by OLS of realized forward-h-day
    variance on the [daily, weekly, monthly] realized-variance components, **refit at each
    step** on only the ``(features, target)`` pairs whose target window closed strictly
    before ``t`` (so no future variance leaks into the fit or the forecast). Until
    ``_HAR_MIN_TRAIN`` such pairs exist it falls back to the EWMA nowcast, so the array is a
    drop-in for :func:`_wf_sigma` — same shape, same look-ahead contract, same "forecast at
    t of forward daily vol" semantics — and feeds the existing band / coverage / correlation
    machinery unchanged.

    ``log=True`` is **log-HAR**: the regression runs on ``log`` realized variance (components
    and target), and the forecast is back-transformed with the causal Jensen correction
    ``E[RV] = exp(μ̂ + ½·resid_var)``. Linear HAR on *raw* variance extrapolates wildly during
    vol explosions (it forecast a negative-R² blow-up on real CL across the 2020 crash); the
    log form is bounded-multiplicative and is the standard robust variant for exactly this.

    Cost note (30d): the OLS is refit every ``_HAR_REFIT`` steps (not per-step) and the beta is
    reused in between — ~5× fewer solves, look-ahead-safe (absolute-index schedule). With that
    perf pass log-HAR is now the live endpoint's default estimator.
    """
    n = rets.size
    sigma = _wf_sigma(rets)  # EWMA fallback for the warm-up region
    if n < _HAR_M + h + _HAR_MIN_TRAIN:
        return sigma  # never enough history to fit — stay pure EWMA
    rv = np.maximum(rets**2, _HAR_FLOOR) if log else rets**2
    x = _har_features(rv)
    if log:
        x = x.copy()
        x[:, 1:] = np.log(x[:, 1:])  # log the three RV components; the intercept stays 1
    # Forward h-day average variance (logged for the log model); realized by index t+h.
    csum = np.concatenate(([0.0], np.cumsum(rv)))
    ytar = np.full(n, np.nan)
    for t in range(n - h):
        mean_rv = (csum[t + 1 + h] - csum[t + 1]) / h
        ytar[t] = np.log(mean_rv) if log else mean_rv
    # First decision point with >= _HAR_MIN_TRAIN training pairs (rows _HAR_M-1 .. d-1-h).
    d_start = _HAR_MIN_TRAIN + h + _HAR_M - 1
    # Periodic refit (30d): recompute beta every _HAR_REFIT steps and reuse it in between. The
    # schedule keys on the absolute index (d - d_start) % _HAR_REFIT, so a truncated prefix hits
    # the same refit points and reuses a beta fit on identical (strictly-older) data → the forecast
    # at d stays prefix-invariant / look-ahead-safe (locked by test_log_har_is_look_ahead_safe).
    beta: np.ndarray | None = None
    resid_var = 0.0  # only used by the log model (Jensen back-transform), cached with beta
    for d in range(d_start, n):
        if beta is None or (d - d_start) % _HAR_REFIT == 0:
            t_max = d - 1 - h  # last t whose target window closed strictly before d
            xtr = x[_HAR_M - 1 : t_max + 1]
            ytr = ytar[_HAR_M - 1 : t_max + 1]
            beta, *_ = np.linalg.lstsq(xtr, ytr, rcond=None)
            if log:
                resid = ytr - xtr @ beta
                resid_var = float(np.mean(resid**2))
        pred = float(x[d] @ beta)
        if log:
            var = float(np.exp(pred + 0.5 * resid_var))  # Jensen back-transform
        else:
            var = pred
        if np.isfinite(var) and var > 0.0:
            sigma[d] = np.sqrt(var)  # else keep the EWMA fallback for this step
    return sigma


# Selectable vol estimators. ``har_log`` (Phase 30b log-HAR) is now the live endpoint **default**
# (Phase 30d): it beats EWMA on real out-of-sample point-forecast R² (mean +5pp across 6
# commodities, fixes the raw-HAR vol-explosion blow-up; see seeds/validate_estimator_30b.py +
# MODEL_DILIGENCE.md) and the 30d periodic-refit perf pass made it cheap enough to serve by
# default. ``ewma`` (cheap single recursive pass, the original Phase 30a band) stays available as
# an explicit opt-out. NOTE: the pure-function ``estimator=`` defaults below stay ``"ewma"`` so the
# EWMA calibration regression tests remain meaningful; the *user-facing* default lives at the
# endpoint Query + the frontend selector.
ESTIMATORS = ("ewma", "har_log")


def _sigma_path(rets: np.ndarray, h: int, estimator: str) -> np.ndarray:
    """Walk-forward daily-vol forecast array for the chosen estimator (look-ahead-safe).

    Both options share the same contract — ``sigma[t]`` is the forecast made at ``t`` of
    forward daily vol — so the band / coverage / correlation machinery is estimator-agnostic.
    """
    if estimator == "har_log":
        return _har_rv_sigma(rets, h, log=True)
    return _wf_sigma(rets)


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


def predict(
    closes: list[float], horizon: str = "1w", estimator: str = "ewma"
) -> RangeForecast | None:
    """Forecast the symmetric price range over `horizon`. None on thin/bad input.

    ``estimator`` selects the vol path: ``"ewma"`` (default — Phase 30a) or ``"har_log"``
    (Phase 30b log-HAR, opt-in — better real-OOS point forecast). The fat-tail band
    multipliers are recomputed against whichever estimator's sigma, so coverage stays
    self-consistent for either choice.
    """
    h = _HORIZON_TDAYS.get(horizon, 5)
    if estimator not in ESTIMATORS:
        estimator = "ewma"
    c = np.asarray(closes, dtype=float)
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return None
    rets = np.diff(np.log(c))
    sigma = _sigma_path(rets, h, estimator)
    sig_d = float(sigma[-1])  # current daily vol forecast = the final walk-forward step
    sig_h = sig_d * float(np.sqrt(h))
    # Fat-tailed band multipliers: the empirical quantiles of past realized standardized
    # moves (full history = look-ahead-safe at serve time), falling back to the normal z
    # until there are enough residuals. Real returns are fat-tailed, so m95 > 1.96 → the
    # 95% band widens to its honest coverage (30c).
    abs_u, _ = _standardized_abs(rets, sigma, h)
    m80 = _multiplier(abs_u, 0.80)
    m95 = _multiplier(abs_u, 0.95)
    empirical = abs_u.size >= _MIN_TAIL
    tail = "+empirical-tails" if empirical else ""
    label = "log-HAR" if estimator == "har_log" else f"EWMA(λ={_LAMBDA})"
    return RangeForecast(
        horizon=horizon,
        sigma_daily=round(sig_d, 6),
        sigma_horizon=round(sig_h, 6),
        band80_low_pct=round(-m80 * sig_h, 5),
        band80_high_pct=round(m80 * sig_h, 5),
        band95_low_pct=round(-m95 * sig_h, 5),
        band95_high_pct=round(m95 * sig_h, 5),
        method=f"{estimator}{tail}",
        note=(
            f"{label} daily vol {sig_d * 100:.2f}% scaled to {horizon} "
            f"(±q·σ·√h, q from {'empirical fat-tail' if empirical else 'normal'} quantiles; "
            f"95%×{m95:.2f}). Symmetric range — no directional claim."
        ),
    )


def walk_forward_coverage(
    closes: list[float],
    horizon: str = "1w",
    levels: tuple[float, ...] = (0.80, 0.95),
    estimator: str = "ewma",
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

    sigma = _sigma_path(rets, h, estimator)
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


def forecast_vol_correlation(
    closes: list[float], horizon: str = "1w", estimator: str = "ewma"
) -> float | None:
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
    sigma = _sigma_path(rets, h, estimator)
    fc = sigma[_WARMUP : n - h]
    rz = np.array(
        [float(np.sqrt(np.mean(rets[t + 1 : t + 1 + h] ** 2))) for t in range(_WARMUP, n - h)]
    )
    if fc.size < 3 or float(np.std(fc)) == 0.0 or float(np.std(rz)) == 0.0:
        return None
    return round(float(np.corrcoef(fc, rz)[0, 1]), 4)


def estimator_skill(closes: list[float], horizon: str = "1w") -> dict[str, object] | None:
    """Walk-forward OOS skill of each vol estimator — the Phase 30b acceptance readout.

    All estimators forecast the **same** target — realized forward h-day daily volatility
    (RMS of the next ``h`` returns) — at the **same** look-ahead-safe decision points (those
    where HAR is genuinely fitting, so the three are scored on an identical sample). For each:
      - ``r2``   : ``1 − SS_res/SS_tot`` against the in-window mean of the target (the constant
        "mean benchmark"). ``r2 > 0`` means the estimator beats that benchmark out-of-sample.
      - ``rmse`` : root-mean-square forecast error, in daily-vol units.

    The gate: HAR-RV clears ``r2 > 0`` **and** a lower RMSE than ``persistence`` (the last
    h-day realized vol — the random-walk vol benchmark). If it only ties persistence within
    noise, the honest call is to keep the simpler EWMA band and bench HAR — the same posture
    as 26b/26c. The 30a result that EWMA point-forecast R² is negative OOS shows up here too;
    this harness exists to see whether HAR flips it positive.

    Honest caveat (as elsewhere here): decision windows overlap, so the metrics are stable
    point estimates whose significance is overstated relative to ``n_eff``. None on thin input.
    """
    h = _HORIZON_TDAYS.get(horizon, 5)
    c = np.asarray(closes, dtype=float)
    if c.size < _MIN_CLOSES or np.any(c <= 0):
        return None
    rets = np.diff(np.log(c))
    n = rets.size
    start = _HAR_MIN_TRAIN + h + _HAR_M - 1  # first index where HAR is genuinely fitting
    if n - h <= start + 2:
        return None  # too little post-warm-up data to score
    ts = range(start, n - h)
    # Shared target: realized forward h-day daily vol (RMS of the next h returns).
    y = np.array([float(np.sqrt(np.mean(rets[t + 1 : t + 1 + h] ** 2))) for t in ts])
    ewma = _wf_sigma(rets)
    har = _har_rv_sigma(rets, h)
    har_log = _har_rv_sigma(rets, h, log=True)
    forecasts: dict[str, np.ndarray] = {
        "ewma": np.array([ewma[t] for t in ts]),
        # persistence = trailing h-day realized vol (the random-walk vol forecast).
        "persistence": np.array(
            [float(np.sqrt(np.mean(rets[t + 1 - h : t + 1] ** 2))) for t in ts]
        ),
        "har_rv": np.array([har[t] for t in ts]),
        "har_log": np.array([har_log[t] for t in ts]),
    }
    ss_tot = float(np.sum((y - y.mean()) ** 2))

    def _score(f: np.ndarray) -> dict[str, float | None]:
        ss_res = float(np.sum((f - y) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
        rmse = float(np.sqrt(np.mean((f - y) ** 2)))
        return {"r2": round(r2, 4) if r2 is not None else None, "rmse": round(rmse, 6)}

    out: dict[str, object] = {
        "horizon": horizon,
        "n": len(y),
        "n_eff": len(range(start, n - h, h)),
        "target": f"forward {h}d daily vol (RMS)",
    }
    for name, f in forecasts.items():
        out[name] = _score(f)
    return out
