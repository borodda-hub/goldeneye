"""Real-data validation of the *directional* models — the symmetric counterpart to
``validate_vol_real.py``.

WHY THIS EXISTS
---------------
Phase 26's headline finding — "no reliable out-of-sample directional edge at any horizon" —
was measured entirely on the synthetic seed. But in that seed the feature generators (COT,
storage, weather) are *causally independent of the price path*, so the price is unpredictable
from features **by construction**. "No directional edge" was therefore partly guaranteed, not
discovered. The vol/range edge already got the real-data treatment (``validate_vol_real.py``);
this gives direction the same honest test, on the half that *can* be tested without real
feature history.

WHAT IT CAN AND CANNOT TEST
---------------------------
- ``moving_average_directional`` and ``holt_trend`` are **price-only** (``inputs_used=["closes"]``)
  → testable right now on real prices.
- ``logreg_directional`` and ``factor_composite`` consume the synthetic COT/storage seeds
  (``backtest._predict`` feeds them ``latest_storage``/``latest_cot``) → **NOT testable** until
  real historical COT + EIA are ingested. That is the documented wall (a deferred phase).

FIDELITY (verified against ``services/backtest.py`` + ``services/signal_scoring.py``)
- Lookback fed to the model = the production ``_LOOKBACK_CLOSES`` = 100 closes.
- Horizon = **calendar** days {1d:1, 1w:7, 1m:30}, realized vs the first close on/after
  ``decision_date + horizon`` (forward-search, ≤7d), anchored on the decision-day close.
- Hit/miss/indeterminate via ``score_forecast`` **verbatim** (±0.3% deadband) — so the verdict
  is directly comparable to the live Signal Lab history table.

Run:
    uv run --directory apps/api python -m seeds.validate_direction_real
"""

from __future__ import annotations

import asyncio
import sys
from bisect import bisect_left
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.seeds.validate_vol_real import _fetch_real_daily_closes  # noqa: E402
from apps.api.services.models.holt_trend import predict as holt_predict  # noqa: E402
from apps.api.services.models.moving_average_directional import (  # noqa: E402
    predict as ma_predict,
)
from apps.api.services.signal_scoring import score_forecast  # noqa: E402

SYMBOLS = ["NG", "CL", "HO", "RB", "GC", "SI"]
HORIZON_DAYS = {"1d": 1, "1w": 7, "1m": 30}  # calendar days — matches backtest._HORIZON_DAYS
MODELS = {"moving_average_directional": ma_predict, "holt_trend": holt_predict}
_LOOKBACK = 100  # backtest._LOOKBACK_CLOSES
_MIN_CLOSES = 55  # backtest._MIN_CLOSES (MA needs SMA-50)
_FWD_SEARCH_CAP_DAYS = 7  # mirror _close_on_or_after's bounded forward search
_CONF_BUCKETS = ("high", "medium", "low")


def _realized_pct(dates: list[date], closes: list[float], t: int, hd: int) -> float | None:
    """(first close on/after date[t]+hd) / close[t] - 1, or None if past the data end."""
    target = dates[t] + timedelta(days=hd)
    u = bisect_left(dates, target)
    if u >= len(dates):
        return None
    if dates[u] > target + timedelta(days=_FWD_SEARCH_CAP_DAYS):
        return None
    start = closes[t]
    return (closes[u] / start) - 1.0 if start > 0 else None


def _run_symbol(
    dates: list[date], closes: list[float]
) -> dict[tuple[str, str], dict[str, object]]:
    """Walk forward over the real series; return per-(model,horizon) tallies."""
    acc: dict[tuple[str, str], dict[str, object]] = {}
    for model in MODELS:
        for hz in HORIZON_DAYS:
            acc[(model, hz)] = {
                "hit": 0, "miss": 0, "indeterminate": 0, "neutral": 0, "pending": 0,
                "up_decisive": 0, "decisive": 0,
                # decisive hits/total per confidence bucket
                "conf": {b: [0, 0] for b in _CONF_BUCKETS},
            }
    n = len(closes)
    for t in range(_MIN_CLOSES - 1, n):
        window = closes[max(0, t + 1 - _LOOKBACK) : t + 1]
        for hz, hd in HORIZON_DAYS.items():
            realized = _realized_pct(dates, closes, t, hd)
            for model, fn in MODELS.items():
                res = fn(window, hz)
                score = score_forecast(res.direction, hz, res.expected_pct, realized)
                a = acc[(model, hz)]
                outcome = score["outcome"]
                a[outcome] = int(a[outcome]) + 1  # type: ignore[arg-type]
                if outcome in ("hit", "miss"):
                    a["decisive"] = int(a["decisive"]) + 1
                    if realized is not None and realized > 0:
                        a["up_decisive"] = int(a["up_decisive"]) + 1
                    bucket = a["conf"][res.confidence]  # type: ignore[index]
                    bucket[1] += 1
                    if outcome == "hit":
                        bucket[0] += 1
    return acc


def _pct(x: float | None) -> str:
    return "  —  " if x is None else f"{x * 100:5.1f}%"


def _print_symbol(sym: str, span: str, acc: dict[tuple[str, str], dict[str, object]]) -> None:
    print(f"\nREAL {sym}=F{span}")
    print(
        f"  {'model':<26}{'hz':<4}{'scored':>7}{'hit_rate':>9}{'decisive':>9}"
        f"{'naive':>7}{'edge':>7}   conf hit% (n)  [high / med / low]"
    )
    for (model, hz), a in acc.items():
        hits, miss, indet = int(a["hit"]), int(a["miss"]), int(a["indeterminate"])
        scored = hits + miss + indet
        hit_rate = hits / scored if scored else None
        decisive_n = int(a["decisive"])
        decisive_acc = hits / decisive_n if decisive_n else None
        up = int(a["up_decisive"]) / decisive_n if decisive_n else None
        naive = max(up, 1.0 - up) if up is not None else None  # best constant-direction call
        edge = (decisive_acc - naive) if (decisive_acc is not None and naive is not None) else None
        conf = a["conf"]  # type: ignore[assignment]
        conf_txt = " / ".join(
            (f"{c[0] / c[1] * 100:4.0f}% ({c[1]})" if c[1] else "  —      ")
            for c in (conf["high"], conf["medium"], conf["low"])  # type: ignore[index]
        )
        edge_txt = "  —  " if edge is None else f"{edge * 100:+5.1f}"
        print(
            f"  {model:<26}{hz:<4}{scored:>7}{_pct(hit_rate):>9}{_pct(decisive_acc):>9}"
            f"{_pct(naive):>7}{edge_txt:>7}   {conf_txt}"
        )


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    print("=" * 78)
    print("Directional models -- REAL-DATA validation (price-only models, ~10y daily)")
    print("=" * 78)
    print("hit_rate = hits/(hit+miss+indet) [production]; decisive = hits/(hit+miss);")
    print("naive = best always-up/always-down call on the same decisive set;")
    print("edge = decisive - naive (≈0 ⇒ no directional edge). conf hit% tests whether")
    print("higher self-rated confidence actually resolves better on REAL data.")

    for sym in SYMBOLS:
        try:
            pairs = await _fetch_real_daily_closes(sym)
        except Exception as exc:  # noqa: BLE001
            print(f"\nREAL {sym}: fetch failed — {type(exc).__name__}: {exc}")
            continue
        if len(pairs) < _MIN_CLOSES + 40:
            print(f"\nREAL {sym}: only {len(pairs)} closes — skipping (too thin).")
            continue
        dates = [date.fromisoformat(d) for d, _ in pairs]
        closes = [c for _, c in pairs]
        acc = _run_symbol(dates, closes)
        _print_symbol(sym, f"  ({pairs[0][0]}→{pairs[-1][0]})", acc)

    print("\n" + "=" * 78)
    print("NOT TESTED HERE (need real feature history — the documented wall):")
    print("  logreg_directional, factor_composite consume synthetic COT/storage seeds.")
    print("  They can only be validated after real historical COT + EIA ingestion")
    print("  (deferred phase). Until then their directional claims are UNVALIDATED.")


if __name__ == "__main__":
    asyncio.run(main())
