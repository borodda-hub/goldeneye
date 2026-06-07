"""Real-data gate for the Phase 30b vol estimator (HAR-RV vs EWMA vs persistence).

WHY THIS EXISTS
---------------
Phase 30a validated that the EWMA vol *band* is calibrated out-of-sample on real data.
30b asks a sharper question about the *point* forecast: can HAR-RV (Corsi 2009 — OLS of
realized forward vol on daily/weekly/monthly realized-variance components) forecast forward
volatility better than the EWMA nowcast and a random-walk persistence benchmark?

Per ``docs/MODEL_DILIGENCE.md`` the synthetic seed is **not evidence** — its regime jumps are
abrupt, which structurally favors a fast EWMA and punishes HAR's 22-day smoothing. Real vol
has gradual long-memory persistence, exactly where HAR historically earns its keep. So the
gate must be decided on real out-of-sample data. This script runs the *unchanged, locked*
``estimator_skill`` from ``services/models/vol_range.py`` on ~10y real daily returns for the
six full-tier commodities, with the synthetic series as a directly-comparable control.

Pre-registered gate (same honest-gate culture as 26b/26c):
  HAR-RV clears r2 > 0 AND a lower RMSE than persistence, on real data → wire it (opt-in).
  Otherwise → keep EWMA, bench HAR (code + tests retained), and say so in MODEL_DILIGENCE.

Run:
    uv run --directory apps/api python -m seeds.validate_estimator_30b
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.seeds.validate_vol_real import (  # noqa: E402
    SYMBOLS,
    _fetch_real_daily_closes,
    _synthetic_ng_closes,
)
from apps.api.services.models.vol_range import estimator_skill  # noqa: E402

HORIZONS = ["1w", "1m"]
_MODELS = ["persistence", "ewma", "har_rv", "har_log"]


def _print_block(label: str, n: int, span: str) -> list[tuple[str, bool | None]]:
    """Print the estimator scoreboard for one series; return per-horizon log-HAR verdicts.

    The decision gate is whether **log-HAR beats the EWMA incumbent** (r2>0 AND lower RMSE
    than EWMA) — that is the question that decides whether HAR earns the default slot.
    """
    print(f"\n{label}  (n={n} closes{span})")
    verdicts: list[tuple[str, bool | None]] = []
    for hz in HORIZONS:
        closes = _CLOSES[label]
        r: Any = estimator_skill(closes, hz)
        if r is None:
            print(f"  {hz}: too thin to score")
            verdicts.append((hz, None))
            continue
        print(f"  {hz}  (n={r['n']} n_eff={r['n_eff']}, target={r['target']})")
        ewma_rmse = r["ewma"]["rmse"]
        for m in _MODELS:
            cell = r[m]
            print(f"     {m:<12} r2={_fmt_r2(cell['r2'])} rmse={cell['rmse']:.6f}")
        hl = r["har_log"]
        beats = hl["r2"] is not None and hl["r2"] > 0 and hl["rmse"] < ewma_rmse
        print(f"     -> log-HAR gate (r2>0 AND rmse<EWMA): {'PASS' if beats else 'FAIL'}")
        verdicts.append((hz, beats))
    return verdicts


def _fmt_r2(v: float | None) -> str:
    return "  n/a " if v is None else f"{v:+.4f}"


_CLOSES: dict[str, list[float]] = {}


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    print("=" * 78)
    print("Phase 30b estimator gate -- HAR-RV vs EWMA vs persistence (locked harness)")
    print("=" * 78)

    syn = _synthetic_ng_closes()
    _CLOSES["SYNTHETIC NG [control]"] = syn
    _print_block("SYNTHETIC NG [control]", len(syn), "")

    print("\n" + "-" * 78)
    print("REAL market data (Yahoo continuous front-month, ~10y daily):")
    all_verdicts: list[tuple[str, str, bool | None]] = []
    for sym in SYMBOLS:
        try:
            pairs = await _fetch_real_daily_closes(sym)
        except Exception as exc:  # noqa: BLE001
            print(f"\nREAL {sym}: fetch failed — {type(exc).__name__}: {exc}")
            continue
        if len(pairs) < 120:
            print(f"\nREAL {sym}: only {len(pairs)} closes — skipping (too thin).")
            continue
        label = f"REAL {sym}=F"
        _CLOSES[label] = [c for _, c in pairs]
        span = f", {pairs[0][0]}→{pairs[-1][0]}"
        for hz, ok in _print_block(label, len(_CLOSES[label]), span):
            all_verdicts.append((sym, hz, ok))

    print("\n" + "=" * 78)
    print("HEADLINE — does log-HAR clear the gate on REAL data?")
    print("=" * 78)
    for hz in HORIZONS:
        rows = [(s, ok) for s, h, ok in all_verdicts if h == hz and ok is not None]
        passes = sum(1 for _, ok in rows if ok)
        print(f"  {hz}: {passes}/{len(rows)} commodities — log-HAR beats EWMA (r2>0, rmse<EWMA)")
    print("\n  If log-HAR does not clearly beat EWMA across commodities, the honest call is")
    print("  to keep EWMA and bench HAR (per docs/MODEL_DILIGENCE.md).")


if __name__ == "__main__":
    asyncio.run(main())
