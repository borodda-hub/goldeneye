"""Implied-vs-forecast vol comparison (Phase D1b) — the SHARED machinery.

The drift-lock philosophy applied to computation: this module owns the
spread / tercile / MAE math for BOTH the D1 research probe
(`seeds/validate_d1_vol_premium.py`, a thin harness over `analyze_pair`)
and the live `GET /v1/vol-premium` surface — so the surface structurally
cannot diverge from what was tested. Gates + the claim split are
pre-registered in `docs/PHASE_D1_PLAN.md §D1b`.

Layer 1 (the comparison — a fact): our walk-forward 1-month realized-vol
forecast vs the market's 30-day implied index, plus the spread's
walk-forward percentile. The SHIP GATE is computed live on every analysis:
our forecast must not be WORSE than the IV index as an RV predictor
(paired MAE delta < +1 SE) or the pair renders its honest note instead.

Layer 2 (conditional context — tested, not crowned): per-tercile
historical premium stats. Displayed with n and SE, never as a signal.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

from apps.api.services.models.vol_range import _sigma_path

# Free implied-vol pairings (same underlying on both sides). There is no
# free NG implied-vol index — NG and other symbols are honestly unsupported.
PAIR_FOR_SYMBOL: dict[str, tuple[str, str]] = {
    "CL": ("USO", "^OVX"),
    "GC": ("GLD", "^GVZ"),
    "ES": ("SPY", "^VIX"),
}

# D1 timing-verdict per underlying (docs/PHASE_D1_PLAN.md §revisit): the
# tercile TIMING claim passed on crude + equities and FAILED on gold. The
# card labels gold's context line accordingly. Changing these requires a
# re-run of the pre-registered gate — see the promotion/demotion rules.
TIMING_TESTED: dict[str, bool] = {"USO": True, "SPY": True, "GLD": False}

H_TDAYS = 21  # matches the IV indices' 30-calendar-day tenor
ANN = float(np.sqrt(252.0))
WARMUP_CLOSES = 260
BUCKET_WARMUP = 52
OVERLAP = 4.2  # weekly steps vs 21d outcomes -> n_eff = n / OVERLAP
FWD_CAP = 7
ESTIMATOR_PRIMARY = "har_log"


@dataclass(frozen=True)
class TercileStat:
    mean: float
    se: float
    n: int


def _se(x: np.ndarray, overlap: float = OVERLAP) -> float:
    n_eff = max(2.0, len(x) / overlap)
    return float(np.std(x, ddof=1) / np.sqrt(n_eff))


def _realized_vol(rets: np.ndarray, start: int) -> float | None:
    w = rets[start : start + H_TDAYS]
    if len(w) < H_TDAYS:
        return None
    return float(np.std(w, ddof=1) * ANN)


def analyze_pair(
    und: dict[str, float], iv: dict[str, float], estimator: str = ESTIMATOR_PRIMARY
) -> dict[str, Any] | None:
    """The single computation both the probe and the live surface use.

    `und` / `iv`: iso-date -> close. Returns the full stats block (weekly
    Friday decisions, walk-forward everything) plus `current` — the latest
    trading day's forecast/IV/spread/percentile — and the live SHIP GATE.
    """
    days = sorted(set(und) & set(iv))
    if len(days) < WARMUP_CLOSES + H_TDAYS + 60:
        return None
    closes = np.array([und[d] for d in days])
    ivs = np.array([iv[d] / 100.0 for d in days])
    rets = np.diff(np.log(closes))
    # sigma[i] is the walk-forward forecast for return i (uses rets[:i]).
    sigma = _sigma_path(rets, H_TDAYS, estimator) * ANN

    rows: list[tuple[int, float, float, float | None]] = []
    for t in range(WARMUP_CLOSES, len(days)):
        if date.fromisoformat(days[t]).weekday() != 4:
            continue
        if t >= len(sigma):
            continue
        rows.append((t, float(sigma[t]), float(ivs[t]), _realized_vol(rets, t)))
    scored = [(t, s, i, rv) for t, s, i, rv in rows if rv is not None]
    if len(scored) < 100:
        return None

    sig_f = np.array([r[1] for r in scored])
    iv_a = np.array([r[2] for r in scored])
    rv_n = np.array([r[3] for r in scored])
    prem = iv_a - rv_n
    spread_hist = np.array([r[1] - r[2] for r in rows])  # incl. unresolved tail

    # G1 / SHIP GATE — paired MAE vs the market's own forecast.
    d = np.abs(sig_f - rv_n) - np.abs(iv_a - rv_n)
    g1_delta, g1_se = float(np.mean(d)), _se(d)

    # Walk-forward expanding terciles of the spread -> subsequent premium.
    spread_scored = sig_f - iv_a
    terciles: dict[str, TercileStat | None] = {}
    buckets = np.full(len(spread_scored), -1)
    for i in range(len(spread_scored)):
        past = spread_scored[:i]
        if len(past) < BUCKET_WARMUP:
            continue
        lo, hi = np.percentile(past, [33.0, 67.0])
        buckets[i] = 0 if spread_scored[i] <= lo else (2 if spread_scored[i] >= hi else 1)
    for k, name in ((0, "low"), (1, "mid"), (2, "high")):
        sel = prem[buckets == k]
        terciles[name] = (
            TercileStat(float(np.mean(sel)), _se(sel), int(len(sel)))
            if len(sel) >= 20
            else None
        )
    g2 = None
    lo_s, hi_s = terciles["low"], terciles["high"]
    if lo_s and hi_s:
        diff = lo_s.mean - hi_s.mean
        dse = float(np.hypot(lo_s.se, hi_s.se))
        mono = (
            terciles["mid"] is not None
            and lo_s.mean > terciles["mid"].mean > hi_s.mean  # type: ignore[union-attr]
        )
        g2 = {"diff": diff, "se": dse, "monotone": bool(mono), "passes": bool(diff > dse and mono)}

    # Current (latest trading day, any weekday) — Layer 1's live numbers.
    current = None
    t_last = len(days) - 1
    if 0 < t_last < len(sigma) + 1 and len(spread_hist) >= BUCKET_WARMUP:
        s_now = float(sigma[min(t_last - 1, len(sigma) - 1)])
        iv_now = float(ivs[t_last])
        spread_now = s_now - iv_now
        pct = float(np.mean(spread_hist <= spread_now) * 100.0)
        lo, hi = np.percentile(spread_hist, [33.0, 67.0])
        bucket = "low" if spread_now <= lo else ("high" if spread_now >= hi else "mid")
        current = {
            "date": days[t_last],
            "sigma_f": s_now,
            "iv": iv_now,
            "spread": spread_now,
            "percentile": pct,
            "bucket": bucket,
        }

    return {
        "n": len(scored),
        "n_eff": round(len(scored) / OVERLAP),
        "span": (days[scored[0][0]], days[scored[-1][0]]),
        "g0_mean_prem": float(np.mean(prem)),
        "g0_share": float(np.mean(prem > 0)),
        "mae_f": float(np.mean(np.abs(sig_f - rv_n))),
        "mae_iv": float(np.mean(np.abs(iv_a - rv_n))),
        "g1_delta": g1_delta,
        "g1_se": g1_se,
        "g1_passes": bool(g1_delta < -g1_se),
        # SHIP GATE (pre-registered): not WORSE than the market's forecast.
        "ship_gate": bool(g1_delta < g1_se),
        "terciles": terciles,
        "g2": g2,
        "current": current,
    }


# ── Live fetch (the surface's data path; probes use their own fetchers) ───

_CACHE_TTL_SECONDS = 6 * 60 * 60  # daily indices — 6h is plenty
_cache: dict[str, tuple[float, dict[str, float]]] = {}


async def _fetch_ticker(ticker: str) -> dict[str, float]:
    from apps.api.adapters._http import AdapterHTTPClient
    from apps.api.adapters.market.yahoo_delayed import (
        _HEADERS,
        YAHOO_BASE_URL,
        _parse_chart,
    )

    now = time.time()
    hit = _cache.get(ticker)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]
    client = AdapterHTTPClient(adapter_name="vol_premium")
    try:
        resp = await client.get(
            YAHOO_BASE_URL + ticker,
            params={"interval": "1d", "range": "12y", "includePrePost": "false"},
            headers=_HEADERS,
        )
        bars = _parse_chart(resp.json(), ticker, "1d")
    finally:
        await client.close()  # type: ignore[no-untyped-call]
    bars.sort(key=lambda b: b["ts"])
    series = {
        b["ts"].date().isoformat(): float(b["close"]) for b in bars if b["close"] > 0
    }
    _cache[ticker] = (now, series)
    return series


async def analyze_symbol(symbol: str) -> dict[str, Any] | None:
    """Live analysis for a supported symbol; None when unsupported/thin."""
    pair = PAIR_FOR_SYMBOL.get(symbol.upper())
    if pair is None:
        return None
    und_t, iv_t = pair
    und = await _fetch_ticker(und_t)
    iv = await _fetch_ticker(iv_t)
    result = analyze_pair(und, iv, ESTIMATOR_PRIMARY)
    if result is None:
        return None
    result["pair"] = {"underlying": und_t, "iv_index": iv_t}
    result["timing_tested"] = TIMING_TESTED.get(und_t, False)
    return result
