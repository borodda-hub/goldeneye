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

D1b NOTE: the spread/tercile/MAE machinery now lives in
`services/vol_premium.py::analyze_pair` — the SAME function the live
`/v1/vol-premium` surface serves. This probe is a thin harness over it, so
the surface structurally cannot diverge from what this file tests.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from apps.api.adapters._http import AdapterHTTPClient  # noqa: E402
from apps.api.adapters.market.yahoo_delayed import (  # noqa: E402
    _HEADERS,
    YAHOO_BASE_URL,
    _parse_chart,
)
from apps.api.services.vol_premium import analyze_pair  # noqa: E402

PAIRS = [("USO", "^OVX"), ("GLD", "^GVZ")]
# Revisit trigger (a), interpretation pre-registered in PHASE_D1_PLAN.md
# BEFORE the run: the third pair is a tie-breaker printed separately — the
# original 2-pair verdict computation above stays untouched.
REVISIT_PAIRS = [("SPY", "^VIX")]
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


def _run_pair(
    und: dict[str, float], iv: dict[str, float], estimator: str
) -> dict | None:
    """Thin harness: the math lives in services/vol_premium.analyze_pair —
    the SAME function the live surface serves (D1b drift-lock). Terciles
    are adapted back to (mean, se, n) tuples for this file's printing."""
    r = analyze_pair(und, iv, estimator)
    if r is None:
        return None
    r["terciles"] = {
        name: ((t.mean, t.se, t.n) if t is not None else None)
        for name, t in r["terciles"].items()
    }
    return r


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

    # ── Revisit tie-breaker (SPY, ^VIX) — har_log only, printed separately ──
    print("\n" + "=" * 92)
    print("D1 REVISIT — tie-breaker pair(s), har_log (interpretation "
          "pre-registered in PHASE_D1_PLAN.md)")
    print("=" * 92)
    revisit_g2: dict[str, bool] = {}
    for und_t, iv_t in REVISIT_PAIRS:
        for t in (und_t, iv_t):
            if t not in data:
                data[t] = await _fetch(t)
                print(f"fetched {t}: {len(data[t])} closes")
        r = _run_pair(data[und_t], data[iv_t], ESTIMATORS[0])
        if r is None:
            print(f"{und_t}/{iv_t}: insufficient data")
            continue
        print(f"\n{und_t} vs {iv_t}  ({r['span'][0]} -> {r['span'][1]}, "
              f"n={r['n']} weekly, n_eff~{r['n_eff']})")
        print(f"  G0 premium: mean(IV - RV_next) = {r['g0_mean_prem'] * 100:+.2f} "
              f"vol-pts, positive {r['g0_share'] * 100:.0f}% of weeks")
        print(f"  G1: MAE(ours)={r['mae_f'] * 100:.2f} vs MAE(IV)="
              f"{r['mae_iv'] * 100:.2f}; d={r['g1_delta'] * 100:+.3f} +/- "
              f"{r['g1_se'] * 100:.3f} -> "
              f"{'BEATS IV' if r['g1_passes'] else 'does NOT beat IV'}")
        for name in ("low", "mid", "high"):
            t3 = r["terciles"][name]
            if t3:
                print(f"    {name:<5} mean={t3[0] * 100:+.2f} +/- {t3[1] * 100:.2f}  n={t3[2]}")
        if r["g2"]:
            print(f"    low-high = {r['g2']['diff'] * 100:+.2f} +/- "
                  f"{r['g2']['se'] * 100:.2f}; monotone="
                  f"{'YES' if r['g2']['monotone'] else 'NO'}  -> "
                  f"{'PASSES' if r['g2']['passes'] else 'fails'}")
        revisit_g2[und_t] = bool(r["g2"] and r["g2"]["passes"])
    hits3 = sum(1 for u, _ in PAIRS if gate_g2.get(u, False)) + sum(
        1 for v in revisit_g2.values() if v
    )
    total3 = len(PAIRS) + len(REVISIT_PAIRS)
    print(f"\n  REVISIT RULE: G2 {hits3}/{total3} -> "
          + ("UPGRADE PARTIAL -> PROMISING (D1b design review; still not a "
             "validated edge)" if hits3 >= 2 else
             "DOWNGRADE crude cell to LIKELY NOISE; park until trigger (b)"))

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
