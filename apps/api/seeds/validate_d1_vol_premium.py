"""Phase D1 — implied-vs-realized vol premium probe (pre-registered gates).

Does the platform's walk-forward realized-vol forecast, compared against the
market's implied vol, carry information about the variance risk premium?
Design + gates pre-registered in docs/PHASE_D1_PLAN.md §gates — read that
before editing anything here; the gate constants are NOT tunable post-hoc.

Pairs (same underlying on both sides): (USO, ^OVX) and (GLD, ^GVZ).
Forecast = `vol_range._sigma_path` (walk-forward; har_log primary, ewma
robustness), annualized. Realized = next-21-trading-day annualized vol.
Weekly Friday decisions; every SE is scaled to n_eff = n / 4.2 (21d outcomes
from 5d steps overlap ~4.2x — never quote raw-n significance).

Manual diagnostic (network) — never CI. Run:
    uv run --directory apps/api python -m seeds.validate_d1_vol_premium
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from apps.api.adapters._http import AdapterHTTPClient  # noqa: E402
from apps.api.adapters.market.yahoo_delayed import (  # noqa: E402
    _HEADERS,
    YAHOO_BASE_URL,
    _parse_chart,
)
from apps.api.services.models.vol_range import _sigma_path  # noqa: E402

PAIRS = [("USO", "^OVX"), ("GLD", "^GVZ")]
H_TDAYS = 21  # matches the indices' 30-calendar-day tenor
ANN = float(np.sqrt(252.0))
WARMUP_CLOSES = 260  # estimator stability before the first decision
BUCKET_WARMUP = 52  # weekly spreads needed before walk-forward terciles
OVERLAP = 4.2  # 21d horizon / 5d step -> n_eff = n / OVERLAP
ESTIMATORS = ("har_log", "ewma")  # primary first (the production default)


async def _fetch(ticker: str) -> dict[str, float]:
    """date-iso -> close for a raw Yahoo ticker (indices use ^ prefixes)."""
    client = AdapterHTTPClient(adapter_name="validate.d1_vol_premium")
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
    return {b["ts"].date().isoformat(): float(b["close"]) for b in bars if b["close"] > 0}


def _se(x: np.ndarray) -> float:
    """Overlap-honest standard error of the mean."""
    n_eff = max(2.0, len(x) / OVERLAP)
    return float(np.std(x, ddof=1) / np.sqrt(n_eff))


def _realized_vol(rets: np.ndarray, start: int) -> float | None:
    w = rets[start : start + H_TDAYS]
    if len(w) < H_TDAYS:
        return None
    return float(np.std(w, ddof=1) * ANN)


def _run_pair(
    und: dict[str, float], iv: dict[str, float], estimator: str
) -> dict | None:
    days = sorted(set(und) & set(iv))
    if len(days) < WARMUP_CLOSES + H_TDAYS + 60:
        return None
    closes = np.array([und[d] for d in days])
    ivs = np.array([iv[d] / 100.0 for d in days])  # index points -> annualized frac
    rets = np.diff(np.log(closes))
    # sigma[i] is the walk-forward forecast for return i (uses rets[:i] only).
    sigma = _sigma_path(rets, H_TDAYS, estimator) * ANN

    rows = []  # (t, sigma_f, iv, rv_next)
    for t in range(WARMUP_CLOSES, len(days)):
        if date.fromisoformat(days[t]).weekday() != 4:  # Friday decisions
            continue
        if t >= len(sigma):
            continue
        rv = _realized_vol(rets, t)  # rets[t:] are strictly after close t
        if rv is None:
            continue
        rows.append((t, float(sigma[t]), float(ivs[t]), rv))
    if len(rows) < 100:
        return None

    sig_f = np.array([r[1] for r in rows])
    iv_a = np.array([r[2] for r in rows])
    rv_n = np.array([r[3] for r in rows])
    prem = iv_a - rv_n

    # G0 — the premium exists (sanity anchor, literature replication).
    g0 = float(np.mean(prem))
    g0_share = float(np.mean(prem > 0))

    # G1 — our forecast vs the market's as an RV predictor (paired MAE).
    d = np.abs(sig_f - rv_n) - np.abs(iv_a - rv_n)
    g1_delta, g1_se = float(np.mean(d)), _se(d)

    # G2 — walk-forward spread terciles -> subsequent premium.
    spread = sig_f - iv_a
    buckets: list[int] = []
    for i in range(len(spread)):
        past = spread[:i]
        if len(past) < BUCKET_WARMUP:
            buckets.append(-1)
            continue
        lo, hi = np.percentile(past, [33.0, 67.0])
        buckets.append(0 if spread[i] <= lo else (2 if spread[i] >= hi else 1))
    b = np.array(buckets)
    terc = {}
    for k, name in ((0, "low"), (1, "mid"), (2, "high")):
        sel = prem[b == k]
        terc[name] = (float(np.mean(sel)), _se(sel), len(sel)) if len(sel) >= 20 else None
    g2 = None
    if terc["low"] and terc["high"]:
        diff = terc["low"][0] - terc["high"][0]
        se = float(np.hypot(terc["low"][1], terc["high"][1]))
        mono = (
            terc["mid"] is not None
            and terc["low"][0] > terc["mid"][0] > terc["high"][0]
        )
        g2 = {"diff": diff, "se": se, "monotone": bool(mono), "passes": bool(diff > se and mono)}

    return {
        "n": len(rows),
        "n_eff": round(len(rows) / OVERLAP),
        "span": (days[rows[0][0]], days[rows[-1][0]]),
        "g0_mean_prem": g0,
        "g0_share": g0_share,
        "mae_f": float(np.mean(np.abs(sig_f - rv_n))),
        "mae_iv": float(np.mean(np.abs(iv_a - rv_n))),
        "g1_delta": g1_delta,
        "g1_se": g1_se,
        "g1_passes": bool(g1_delta < -g1_se),
        "terciles": terc,
        "g2": g2,
    }


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

    data: dict[str, dict[str, float]] = {}
    for und_t, iv_t in PAIRS:
        for t in (und_t, iv_t):
            if t not in data:
                data[t] = await _fetch(t)
                print(f"fetched {t}: {len(data[t])} closes")

    gate_g1: dict[str, bool] = {}
    gate_g2: dict[str, bool] = {}
    for estimator in ESTIMATORS:
        primary = estimator == ESTIMATORS[0]
        print("\n" + "=" * 92)
        print(f"D1 — variance-risk-premium probe — estimator = {estimator}"
              f"{'  (PRIMARY — gate estimator)' if primary else '  (robustness)'}")
        print("=" * 92)
        for und_t, iv_t in PAIRS:
            r = _run_pair(data[und_t], data[iv_t], estimator)
            if r is None:
                print(f"{und_t}/{iv_t}: insufficient data")
                continue
            print(f"\n{und_t} vs {iv_t}  ({r['span'][0]} -> {r['span'][1]}, "
                  f"n={r['n']} weekly, n_eff~{r['n_eff']})")
            print(f"  G0 premium: mean(IV - RV_next) = {r['g0_mean_prem'] * 100:+.2f} "
                  f"vol-pts, positive {r['g0_share'] * 100:.0f}% of weeks")
            print(f"  G1 RV-forecast skill: MAE(ours)={r['mae_f'] * 100:.2f} vs "
                  f"MAE(IV)={r['mae_iv'] * 100:.2f} vol-pts; paired d = "
                  f"{r['g1_delta'] * 100:+.3f} +/- {r['g1_se'] * 100:.3f}  -> "
                  f"{'BEATS IV (>1 SE)' if r['g1_passes'] else 'does NOT beat IV'}")
            print("  G2 spread terciles (walk-forward) -> subsequent premium (vol-pts):")
            for name in ("low", "mid", "high"):
                t3 = r["terciles"][name]
                if t3:
                    print(f"    {name:<5} mean={t3[0] * 100:+.2f} +/- {t3[1] * 100:.2f}  n={t3[2]}")
            if r["g2"]:
                print(f"    low-high = {r['g2']['diff'] * 100:+.2f} +/- "
                      f"{r['g2']['se'] * 100:.2f}; monotone={'YES' if r['g2']['monotone'] else 'NO'}"
                      f"  -> {'PASSES' if r['g2']['passes'] else 'fails'}")
            if primary:
                gate_g1[und_t] = r["g1_passes"]
                gate_g2[und_t] = bool(r["g2"] and r["g2"]["passes"])

    g1_all = all(gate_g1.get(u, False) for u, _ in PAIRS)
    g2_hits = sum(1 for u, _ in PAIRS if gate_g2.get(u, False))
    print("\n" + "=" * 92)
    print("PRE-REGISTERED VERDICT (docs/PHASE_D1_PLAN.md §gates, har_log):")
    print(f"  G1 both assets: {'YES' if g1_all else 'NO'}   G2 assets passing: {g2_hits}/2")
    if g1_all and g2_hits == 2:
        print("  >>> PASS — conditional vol-premium information; scope D1b <<<")
    elif g2_hits == 1:
        print("  >>> PARTIAL — G2 on one asset only; record, no build, revisit <<<")
    else:
        print("  >>> FAIL — no premium-timing edge; record and bench <<<")


if __name__ == "__main__":
    asyncio.run(main())
