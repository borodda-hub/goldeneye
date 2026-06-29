"""Honest out-of-sample scorecard for the WHOLE forecast engine — directional skill
+ vol/range calibration — on real data, in one run.

The umbrella over ``validate_direction_real.py`` (directional, price-only) and
``validate_vol_real.py`` (vol coverage): it scores **all five voter models + the
ensemble** for direction AND the vol/range bands, per-commodity and pooled, each
metric reported NEXT TO its baseline so the number can't flatter itself.

WHY IT EXISTS
-------------
"Does the engine actually predict?" deserves a single, no-cherry-pick answer on real
out-of-sample data. This produces that table. It is a *measurement*, not a claim
generator — it changes nothing and recommends nothing; read the numbers.

LOOK-AHEAD SAFETY
-----------------
Walk-forward only: every prediction sees a strictly-past window
(``closes[max(0, t+1-LOOKBACK):t+1]``) — identical to the production
``_LOOKBACK_CLOSES`` path and to ``validate_direction_real``. The models are pure
functions of that window; the cheating-model proof (``tests/test_backtest_lookahead.py``)
guards the engine's chokepoint. No future bar is ever visible.

WHAT IT CAN / CANNOT TEST
-------------------------
- ``ma_cross``, ``vol_regime``, ``holt`` are price-only → fully testable.
- ``logreg`` and ``factor_composite`` are run **price-only here** (``latest_storage`` /
  ``latest_cot`` = None): this tests their PRICE behaviour. Their alt-data legs
  (COT/storage) stay UNVALIDATED until real feature history is ingested (Phase 31/C3);
  marked with ``*`` in the output. See ``docs/MODEL_DILIGENCE.md``.

COLUMNS
-------
- ``base%``       base rate of up-moves in the sample (the drift; the bar to beat).
- ``dec_acc%``    decisive hit-rate WITH the production ±0.3% deadband (drops neutral
                  calls + |realized| < 0.3%).
- ``frcd_acc%``   forced hit-rate with NO deadband (every day scored from expected-move
                  sign). If ``dec_acc`` >> ``frcd_acc``, the deadband is flattering.
- ``edge%``       ``dec_acc`` − best-constant baseline (always-up/down on the same set).
                  ≈0 ⇒ no edge; <0 ⇒ worse than a constant guess.
- ``Brier``/``skill%``  Brier on the (imposed) directional probabilities and the skill
                  score 1 − Brier/baseline-Brier (baseline = always predict ``base``).
                  NOTE: the models are not natively probabilistic, so the prob mapping
                  below is IMPOSED — the skill *sign* is robust, the absolute Brier isn't.
- vol ``cov80/cov95``  fraction of realized moves inside the 80% / 95% band
                  (calibrated = ~80 / ~95).

Run (needs network + a few minutes; not a CI test):
    uv run --directory apps/api python -m seeds.validate_engine_oos
"""

from __future__ import annotations

import asyncio
import sys
from bisect import bisect_left
from datetime import date, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from apps.api.seeds.validate_vol_real import _fetch_real_daily_closes  # noqa: E402
from apps.api.services.ensemble import compute_ensemble  # noqa: E402
from apps.api.services.models.factor_composite import predict as factor_p  # noqa: E402
from apps.api.services.models.holt_trend import predict as holt_p  # noqa: E402
from apps.api.services.models.logreg_directional import predict as logreg_p  # noqa: E402
from apps.api.services.models.moving_average_directional import predict as ma_p  # noqa: E402
from apps.api.services.models.vol_range import walk_forward_coverage  # noqa: E402
from apps.api.services.models.volatility_regime import classify as classify_reg  # noqa: E402
from apps.api.services.models.volatility_regime import predict as volreg_p  # noqa: E402

SYMBOLS = ["NG", "CL", "HO", "RB", "GC", "SI"]  # the 6 full-tier commodities
HZ = {"1d": 1, "1w": 7, "1m": 30}  # calendar days (matches backtest._HORIZON_DAYS)
LOOKBACK, MIN_CLOSES, FWD_CAP = 100, 55, 7
MODELS = ["ma_cross", "vol_regime", "holt", "logreg*", "factor*", "ENSEMBLE"]

# Pre-stated (direction, confidence) -> P(up). Imposed (models aren't probabilistic):
# the SKILL SIGN is robust to it; the absolute Brier is mapping-dependent.
PMAP = {
    ("bullish", "high"): 0.65, ("bullish", "medium"): 0.58, ("bullish", "low"): 0.53,
    ("bearish", "high"): 0.35, ("bearish", "medium"): 0.42, ("bearish", "low"): 0.47,
}


def _p_up(direction: str, conf: str) -> float:
    return PMAP.get((direction, conf), 0.50)


def _realized_pct(dates, closes, t, hd):
    target = dates[t] + timedelta(days=hd)
    u = bisect_left(dates, target)
    if u >= len(dates) or dates[u] > target + timedelta(days=FWD_CAP):
        return None
    s = closes[t]
    return (closes[u] / s - 1.0) if s > 0 else None


def _model_calls(window, hz):
    """{model: (direction, confidence, expected_pct)} incl. ensemble — production calls."""
    ma, ho, fa, lo, vr = (
        ma_p(window, hz), holt_p(window, hz), factor_p(window, hz, None, None),
        logreg_p(window, hz), volreg_p(window, hz),
    )
    reg = classify_reg(window)
    voters = [ma, ho, fa, lo]
    for r in voters:
        r.vol_regime = reg
    ens = compute_ensemble(voters)
    return {
        "ma_cross": (ma.direction, ma.confidence, ma.expected_pct),
        "vol_regime": (vr.direction, vr.confidence, vr.expected_pct),
        "holt": (ho.direction, ho.confidence, ho.expected_pct),
        "logreg*": (lo.direction, lo.confidence, lo.expected_pct),
        "factor*": (fa.direction, fa.confidence, fa.expected_pct),
        "ENSEMBLE": (ens["direction"], ens["confidence"], ens.get("expected_pct")),
    }


def _new_cell():
    return {"ru": [], "pup": [], "dec": [], "forced": []}


def _accumulate(acc, dates, closes):
    n = len(closes)
    for t in range(MIN_CLOSES - 1, n):
        window = closes[max(0, t + 1 - LOOKBACK):t + 1]
        per_hz = {hz: _model_calls(window, hz) for hz in HZ}
        for hz, hd in HZ.items():
            r = _realized_pct(dates, closes, t, hd)
            if r is None:
                continue
            ru = 1 if r > 0 else 0
            for m, (dirn, conf, exp) in per_hz[hz].items():
                c = acc[(m, hz)]
                c["ru"].append(ru)
                c["pup"].append(_p_up(dirn, conf))
                if exp is not None and exp != 0:
                    fpred = 1 if exp > 0 else 0
                elif dirn == "bullish":
                    fpred = 1
                elif dirn == "bearish":
                    fpred = 0
                else:
                    fpred = None
                if fpred is not None:
                    c["forced"].append((fpred, ru))
                if dirn in ("bullish", "bearish") and abs(r) >= 0.003:
                    c["dec"].append((1 if dirn == "bullish" else 0, ru))


def _brier(pups, rus):
    return sum((p - y) ** 2 for p, y in zip(pups, rus)) / len(pups) if pups else None


def _metrics(c):
    ru, pup, dec, forced = c["ru"], c["pup"], c["dec"], c["forced"]
    n = len(ru)
    if n == 0:
        return None
    base = sum(ru) / n
    dec_acc = sum(1 for pr, y in dec if pr == y) / len(dec) if dec else None
    dec_base = sum(y for _, y in dec) / len(dec) if dec else None
    dec_const = max(dec_base, 1 - dec_base) if dec_base is not None else None
    edge = (dec_acc - dec_const) if (dec_acc is not None and dec_const is not None) else None
    forced_acc = sum(1 for pr, y in forced if pr == y) / len(forced) if forced else None
    b = _brier(pup, ru)
    bbase = _brier([base] * n, ru)
    skill = (1 - b / bbase) if (b is not None and bbase) else None
    return {
        "n": n, "base": base, "dec_n": len(dec), "dec_acc": dec_acc,
        "forced_acc": forced_acc, "edge": edge, "brier": b, "skill": skill,
    }


def _pc(x):
    return "  —  " if x is None else f"{x * 100:5.1f}"


def _signed(x):
    return "  —" if x is None else f"{x * 100:+.1f}"


def _brier_s(b):
    return "  —  " if not b else f"{b:.4f}"


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

    pooled = {(m, hz): _new_cell() for m in MODELS for hz in HZ}
    per_sym: dict[str, dict] = {}
    cov: dict[str, dict] = {}
    for sym in SYMBOLS:
        try:
            pairs = await _fetch_real_daily_closes(sym)
        except Exception as e:  # noqa: BLE001
            print(f"{sym}: fetch failed — {type(e).__name__}: {e}")
            continue
        if len(pairs) < MIN_CLOSES + 40:
            print(f"{sym}: too thin ({len(pairs)}) — skipping")
            continue
        dates = [date.fromisoformat(d) for d, _ in pairs]
        closes = [c for _, c in pairs]
        acc = {(m, hz): _new_cell() for m in MODELS for hz in HZ}
        _accumulate(acc, dates, closes)
        per_sym[sym] = {k: _metrics(v) for k, v in acc.items()}
        for k in pooled:
            for f in ("ru", "pup", "dec", "forced"):
                pooled[k][f].extend(acc[k][f])
        cov[sym] = {h: walk_forward_coverage(closes, horizon=h) for h in ("1w", "1m")}
        print(f"  done {sym} ({pairs[0][0]}->{pairs[-1][0]}, {len(closes)} closes)")

    print("\n" + "=" * 100)
    print(f"DIRECTIONAL — POOLED across {len(per_sym)} commodities, walk-forward OOS, real ~10y")
    print("=" * 100)
    print(f"{'model':<11}{'hz':<4}{'n':>7}{'base%':>7}{'dec_n':>7}{'dec_acc%':>9}"
          f"{'frcd_acc%':>10}{'edge%':>7}{'Brier':>8}{'skill%':>8}  flag")
    for m in MODELS:
        for hz in HZ:
            x = _metrics(pooled[(m, hz)])
            if not x:
                continue
            flag = "SMALL-n" if x["dec_n"] < 100 else ""
            print(f"{m:<11}{hz:<4}{x['n']:>7}{_pc(x['base']):>7}{x['dec_n']:>7}"
                  f"{_pc(x['dec_acc']):>9}{_pc(x['forced_acc']):>10}{_signed(x['edge']):>7}"
                  f"{_brier_s(x['brier']):>8}{_signed(x['skill']):>8}  {flag}")
    print("\nedge ≈ 0 ⇒ no edge; <0 ⇒ worse than a constant guess. dec_acc≈frcd_acc ⇒ deadband")
    print("is NOT flattering. 1w/1m windows overlap → effective n well below the raw count.")

    print("\n" + "=" * 100)
    print("DIRECTIONAL — per-commodity ENSEMBLE (1w) — consistency (no cherry-pick)")
    print("=" * 100)
    print(f"{'sym':<5}{'dec_n':>7}{'dec_acc%':>9}{'base%':>7}{'edge%':>7}{'skill%':>8}")
    for sym in per_sym:
        x = per_sym[sym][("ENSEMBLE", "1w")]
        if x:
            print(f"{sym:<5}{x['dec_n']:>7}{_pc(x['dec_acc']):>9}{_pc(x['base']):>7}"
                  f"{_signed(x['edge']):>7}{_signed(x['skill']):>8}")

    print("\n" + "=" * 100)
    print("VOL / RANGE band coverage (calibrated = 80%->~80%, 95%->~95%) — real OOS")
    print("=" * 100)
    print(f"{'sym':<5}{'1w c80':>9}{'1w c95':>9}{'n_eff':>8}{'1m c80':>9}{'1m c95':>9}")
    agg = {"1w": [[], []], "1m": [[], []]}
    for sym in cov:
        for h in ("1w", "1m"):
            agg[h][0].append(cov[sym][h].get("cov80"))
            agg[h][1].append(cov[sym][h].get("cov95"))
        c1, c2 = cov[sym]["1w"], cov[sym]["1m"]
        print(f"{sym:<5}{_pc(c1.get('cov80')):>9}{_pc(c1.get('cov95')):>9}"
              f"{c1.get('n_eff', 0):>8}{_pc(c2.get('cov80')):>9}{_pc(c2.get('cov95')):>9}")
    for h in ("1w", "1m"):
        v80 = [x for x in agg[h][0] if x is not None]
        v95 = [x for x in agg[h][1] if x is not None]
        m80 = sum(v80) / len(v80) if v80 else None
        m95 = sum(v95) / len(v95) if v95 else None
        print(f"MEAN {h}: cov80={_pc(m80)}  cov95={_pc(m95)}")


if __name__ == "__main__":
    asyncio.run(main())
