"""Real-data validation of the Phase 30a vol/range edge.

WHY THIS EXISTS
---------------
Every Phase 30a "calibrated edge" number (80% coverage, +0.30–0.42 forecast/realized
vol correlation) was measured on the *synthetic* regime-switching GBM series from
``seeds/price_generator.py``. That series has volatility clustering injected by
construction (a Markov chain over 4 vol regimes), and the forecaster is an EWMA — the
exact tool for detecting clustered vol. So the synthetic result is partly tautological:
we built data with the property, then measured that our detector detects it.

This script answers the only question that matters for diligence: **does the same edge
survive on REAL out-of-sample market returns?** It fetches real daily history for the
six full-tier commodities through the production Yahoo adapter path, then runs the
*unchanged, locked* harness functions from ``services/models/vol_range.py`` on real
closes. The synthetic NG series is run alongside as a control so the two are directly
comparable.

Nothing here changes the model. It only feeds real data into the existing tests.

Run:
    uv run --directory apps/api python -m seeds.validate_vol_real
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.adapters._http import AdapterHTTPClient  # noqa: E402
from apps.api.adapters.market.yahoo_delayed import (  # noqa: E402
    _HEADERS,
    YAHOO_BASE_URL,
    _parse_chart,
)
from apps.api.services.models.vol_range import (  # noqa: E402
    forecast_vol_correlation,
    walk_forward_coverage,
)

# Full-tier commodities. Continuous front-month tickers ("<SYM>=F") — the right series
# for a vol study (no within-delivery-month roll gaps).
SYMBOLS = ["NG", "CL", "HO", "RB", "GC", "SI"]
HORIZONS = ["1d", "1w", "1m"]

# Acceptance band for the 80% interval (the locked synthetic gate is [0.77, 0.83];
# we widen the *reporting* band slightly for real data — markets have fatter tails —
# but flag anything outside the original gate honestly).
GATE_80 = (0.77, 0.83)


async def _fetch_real_daily_closes(sym: str, years: str = "10y") -> list[tuple[str, float]]:
    """Real daily (date, close) for the continuous front-month, oldest→newest.

    Uses the production Yahoo HTTP client + chart parser; only the range is widened
    beyond the adapter's 1y default so the walk-forward has enough independent windows.
    """
    client = AdapterHTTPClient(adapter_name="validate.vol_real")
    ticker = f"{sym}=F"
    try:
        resp = await client.get(
            YAHOO_BASE_URL + ticker,
            params={"interval": "1d", "range": years, "includePrePost": "false"},
            headers=_HEADERS,
        )
        bars = _parse_chart(resp.json(), ticker, "1d")
    finally:
        await client.close()  # type: ignore[no-untyped-call]
    bars.sort(key=lambda b: b["ts"])
    return [(b["ts"].date().isoformat(), float(b["close"])) for b in bars if b["close"] > 0]


def _synthetic_ng_closes() -> list[float]:
    """The synthetic NG daily closes every Phase 30a claim was measured on."""
    from apps.api.seeds.price_generator import generate

    daily = [b for b in generate()["bars"] if b["resolution"] == "1d"]
    daily.sort(key=lambda b: b["ts"])
    return [float(b["close"]) for b in daily]


def _run_harness(closes: list[float]) -> dict[str, dict[str, float | None]]:
    """Run the unchanged locked functions for every horizon."""
    out: dict[str, dict[str, float | None]] = {}
    for h in HORIZONS:
        cov = walk_forward_coverage(closes, horizon=h)
        out[h] = {
            "cov80": cov.get("cov80"),
            "cov95": cov.get("cov95"),
            "n_eff": cov.get("n_eff"),
            "corr": forecast_vol_correlation(closes, horizon=h),
        }
    return out


def _fmt(v: float | None, pct: bool = False) -> str:
    if v is None:
        return "   —  "
    return f"{v * 100:5.1f}%" if pct else f"{v:6.3f}"


def _verdict(cov80: float | None) -> str:
    if cov80 is None:
        return "n/a"
    lo, hi = GATE_80
    if lo <= cov80 <= hi:
        return "PASS (in [77,83])"
    if cov80 < lo:
        return f"UNDER ({cov80 * 100:.0f}% < 77 — band too tight, real tails)"
    return f"OVER ({cov80 * 100:.0f}% > 83 — band too wide)"


def _print_block(label: str, n: int, span: str, res: dict[str, dict[str, float | None]]) -> None:
    print(f"\n{label}  (n={n} closes{span})")
    print(f"  {'horizon':<8}{'cov80':>8}{'cov95':>8}{'n_eff':>8}{'fwd-corr':>10}   verdict(80%)")
    for h in HORIZONS:
        r = res[h]
        n_eff = r["n_eff"]
        print(
            f"  {h:<8}{_fmt(r['cov80'], pct=True):>8}{_fmt(r['cov95'], pct=True):>8}"
            f"{int(n_eff) if n_eff is not None else 0:>8}{_fmt(r['corr']):>10}"
            f"   {_verdict(r['cov80'])}"
        )


async def main() -> None:
    # Windows consoles default to cp1252 and choke on non-ASCII; force UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    print("=" * 78)
    print("Phase 30a vol/range edge -- REAL-DATA validation (unchanged locked harness)")
    print("=" * 78)

    # Control: the synthetic series every claim was measured on.
    syn = _synthetic_ng_closes()
    _print_block("SYNTHETIC NG  [control: seed=42 regime GBM]", len(syn), "", _run_harness(syn))

    # Real data, one symbol at a time (sequential — gentle on the unofficial endpoint).
    print("\n" + "-" * 78)
    print("REAL market data (Yahoo continuous front-month, ~10y daily):")
    real_summary: list[tuple[str, float | None]] = []
    for sym in SYMBOLS:
        try:
            pairs = await _fetch_real_daily_closes(sym)
        except Exception as exc:  # noqa: BLE001
            print(f"\nREAL {sym}: fetch failed — {type(exc).__name__}: {exc}")
            real_summary.append((sym, None))
            continue
        if len(pairs) < 60:
            print(f"\nREAL {sym}: only {len(pairs)} closes returned — skipping (too thin).")
            real_summary.append((sym, None))
            continue
        closes = [c for _, c in pairs]
        span = f", {pairs[0][0]}→{pairs[-1][0]}"
        res = _run_harness(closes)
        _print_block(f"REAL {sym}=F", len(closes), span, res)
        real_summary.append((sym, res["1w"]["cov80"]))

    # Headline.
    print("\n" + "=" * 78)
    print("HEADLINE — does the 80% band hold out-of-sample on REAL data? (1w horizon)")
    print("=" * 78)
    passes = 0
    total = 0
    for sym, cov in real_summary:
        if cov is None:
            print(f"  {sym:<4} —   (no data)")
            continue
        total += 1
        ok = GATE_80[0] <= cov <= GATE_80[1]
        passes += int(ok)
        print(f"  {sym:<4} {cov * 100:5.1f}%   {'PASS' if ok else 'FAIL'}")
    print(f"\n  {passes}/{total} real commodities pass the original [77,83]% 80%-coverage gate.")
    print("  Read this against the synthetic control above. If real coverage is")
    print("  systematically UNDER 77%, the normal-band assumption breaks on real fat")
    print("  tails (→ Phase 30c) and 'calibrated edge' is not yet a real-data claim.")


if __name__ == "__main__":
    asyncio.run(main())
