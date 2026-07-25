"""Phase D2b — carry/term-structure probe (pre-registered gates).

Does the futures-curve slope (backwardation/contango) predict forward
front-month direction? Gates pre-registered in docs/PHASE_D2_PLAN.md —
committed before the first run; the power rule (P0) and gate constants are
NOT tunable post-hoc.

Curve source: OUR DB's per-contract real dailies (`price_bars`,
source='yahoo_delayed') — the only free path to any historical curve, since
Yahoo drops expired months (plan §[V]). At date t the slope uses the two
nearest-expiry contracts with bars at t; for older dates that pair sits
further out the curve (deferred-slope proxy — a coverage limitation, not
look-ahead: those contracts were listed and priced at t).

Run AFTER the deep month backfill:
    uv run --directory apps/api python -m seeds.backfill_prices NG CL --lookback-days 1825
    uv run --directory apps/api python -m seeds.validate_d2_carry
"""

from __future__ import annotations

import asyncio
import sys
from bisect import bisect_left
from datetime import date, timedelta
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from apps.api.seeds.validate_vol_real import _fetch_real_daily_closes  # noqa: E402

SYMBOLS = ["NG", "CL"]
HZ = {"1w": 7, "1m": 30}  # calendar days; 1m is PRIMARY (carry is slow)
OVERLAP = {"1w": 1.0, "1m": 4.3}  # weekly steps: 1w non-overlapping, 1m ~4.3x
P0_MIN_NEFF = 60  # pooled 1m power rule — below this: INSUFFICIENT-N
BUCKET_WARMUP = 52
FWD_CAP = 7
# Imposed carry probabilities (medium-tier, matching the engine's PMAP row).
P_BULL, P_BEAR = 0.58, 0.42
DRIFT_WINDOW = 100


async def _direct_contract_history(code: str) -> dict[date, float]:
    """Full available history for one contract month via the chart API
    directly (the market adapter caps its range ~1y; Yahoo itself serves ~5y
    for LISTED months and nothing for expired ones — plan §[V]). Expired →
    empty dict; the DB bars cover their lifetime instead."""
    from apps.api.adapters._http import AdapterHTTPClient
    from apps.api.adapters.market.yahoo_delayed import (
        _HEADERS,
        YAHOO_BASE_URL,
        _parse_chart,
    )

    ticker = f"{code}.NYM"  # NG/CL months trade on NYMEX
    client = AdapterHTTPClient(adapter_name="validate.d2_carry")
    try:
        resp = await client.get(
            YAHOO_BASE_URL + ticker,
            params={"interval": "1d", "range": "5y", "includePrePost": "false"},
            headers=_HEADERS,
        )
        bars = _parse_chart(resp.json(), ticker, "1d")
    except Exception:  # noqa: BLE001 — expired months 404; DB covers them
        return {}
    finally:
        await client.close()  # type: ignore[no-untyped-call]
    return {b["ts"].date(): float(b["close"]) for b in bars if b["close"] > 0}


async def _curve_series(symbol: str) -> dict[date, float]:
    """date -> annualized log slope from the two nearest-expiry contracts
    priced on that date. Prices = DB per-contract real bars (the archive
    keeps expired months) MERGED with direct 5y fetches for listed months
    (deeper than the adapter-capped DB coverage)."""
    from sqlalchemy import select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.contracts import Contract
    from apps.api.models.orm.instruments import Instrument
    from apps.api.models.orm.prices import PriceBar

    async with get_session_factory()() as session:
        rows = (
            await session.execute(
                select(
                    PriceBar.ts, PriceBar.close, Contract.expiry_date, Contract.contract_code
                )
                .join(Contract, Contract.id == PriceBar.contract_id)
                .join(Instrument, Instrument.id == Contract.instrument_id)
                .where(
                    Instrument.symbol == symbol,
                    PriceBar.resolution == "1d",
                    PriceBar.source == "yahoo_delayed",
                )
            )
        ).all()
    # Per-contract series: DB bars first...
    per_contract: dict[str, tuple[date, dict[date, float]]] = {}
    for ts, close, expiry, code in rows:
        d = ts.date()
        if close and float(close) > 0:
            per_contract.setdefault(code, (expiry, {}))[1][d] = float(close)
    # ...then deepen each listed month via the direct 5y path (DB wins ties —
    # values are identical; expired months return empty and keep DB coverage).
    for code, (expiry, series) in per_contract.items():
        deep = await _direct_contract_history(code)
        for d, px in deep.items():
            series.setdefault(d, px)

    by_day: dict[date, list[tuple[date, float]]] = {}
    for _code, (expiry, series) in per_contract.items():
        for d, px in series.items():
            if expiry > d:
                by_day.setdefault(d, []).append((expiry, px))
    slopes: dict[date, float] = {}
    for d, legs in by_day.items():
        legs.sort()
        if len(legs) < 2:
            continue
        (e_near, p_near), (e_far, p_far) = legs[0], legs[1]
        dt_years = (e_far - e_near).days / 365.25
        if dt_years <= 0:
            continue
        slopes[d] = float(np.log(p_far / p_near) / dt_years)
    return slopes


def _fwd_ret(dates: list[date], closes: list[float], t: int, hd: int) -> float | None:
    target = dates[t] + timedelta(days=hd)
    u = bisect_left(dates, target)
    if u >= len(dates) or dates[u] > target + timedelta(days=FWD_CAP):
        return None
    return closes[u] / closes[t] - 1.0


def _se(x: np.ndarray, overlap: float) -> float:
    n_eff = max(2.0, len(x) / overlap)
    return float(np.std(x, ddof=1) / np.sqrt(n_eff))


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

    pooled: dict[str, dict[str, list]] = {
        hz: {"d_brier": [], "carry_hit": [], "drift_hit": []} for hz in HZ
    }
    per_sym_g2: dict[str, dict] = {}
    pooled_n_1m = 0

    for sym in SYMBOLS:
        slopes = await _curve_series(sym)
        pairs = await _fetch_real_daily_closes(sym)
        dates = [date.fromisoformat(d) for d, _ in pairs]
        closes = [c for _, c in pairs]
        print(f"{sym}: curve days={len(slopes)} "
              f"({min(slopes) if slopes else '—'} -> {max(slopes) if slopes else '—'}), "
              f"continuous closes={len(closes)}")

        # Weekly Friday decisions where a slope exists.
        decisions: list[tuple[int, float]] = []
        for t in range(DRIFT_WINDOW, len(dates)):
            if dates[t].weekday() != 4:
                continue
            s = slopes.get(dates[t])
            if s is None:
                continue
            decisions.append((t, s))
        spread = np.array([s for _, s in decisions])

        g2_rows = {hz: {0: [], 1: [], 2: []} for hz in HZ}
        for i, (t, s) in enumerate(decisions):
            rets = np.diff(np.log(closes[t - DRIFT_WINDOW : t + 1]))
            drift_p = float(np.mean(rets > 0))
            carry_p = P_BULL if s < 0 else P_BEAR  # backwardation -> bullish
            past = spread[:i]
            bucket = None
            if len(past) >= BUCKET_WARMUP:
                lo, hi = np.percentile(past, [33.0, 67.0])
                bucket = 0 if s <= lo else (2 if s >= hi else 1)
            for hz, hd in HZ.items():
                r = _fwd_ret(dates, closes, t, hd)
                if r is None:
                    continue
                y = 1 if r > 0 else 0
                pooled[hz]["d_brier"].append(
                    (carry_p - y) ** 2 - (drift_p - y) ** 2
                )
                pooled[hz]["carry_hit"].append(1 if (s < 0) == (y == 1) else 0)
                pooled[hz]["drift_hit"].append(
                    1 if (drift_p > 0.5) == (y == 1) else 0
                )
                if hz == "1m":
                    pooled_n_1m += 1
                if bucket is not None:
                    g2_rows[hz][bucket].append(r)
        per_sym_g2[sym] = g2_rows

    print("\n" + "=" * 92)
    print("D2b — carry probe, pooled NG+CL (weekly Friday decisions)")
    print("=" * 92)
    for hz in HZ:
        d = np.array(pooled[hz]["d_brier"])
        if len(d) < 10:
            print(f"{hz}: insufficient rows")
            continue
        n_eff = round(len(d) / OVERLAP[hz])
        ch = float(np.mean(pooled[hz]["carry_hit"]))
        dh = float(np.mean(pooled[hz]["drift_hit"]))
        dm, dse = float(np.mean(d)), _se(d, OVERLAP[hz])
        print(f"{hz}: n={len(d)} n_eff~{n_eff}  carry_hit={ch * 100:.1f}%  "
              f"drift_hit={dh * 100:.1f}%  dBrier(carry-drift)={dm:+.5f} +/- {dse:.5f}"
              f"  -> {'carry BEATS drift (>1 SE)' if dm < -dse else 'does NOT beat drift'}")

    print("\nG2 — forward 1m return by walk-forward slope tercile (per symbol):")
    g2_pass = {}
    for sym in SYMBOLS:
        rows = per_sym_g2[sym]["1m"]
        stats = {}
        for k, name in ((0, "low(bwd)"), (1, "mid"), (2, "high(cntgo)")):
            x = np.array(rows[k])
            stats[k] = (float(np.mean(x)), _se(x, OVERLAP["1m"]), len(x)) if len(x) >= 15 else None
        line = f"  {sym}: "
        for k, name in ((0, "low(bwd)"), (1, "mid"), (2, "high(cntgo)")):
            line += (f"{name} {stats[k][0] * 100:+.2f}%±{stats[k][1] * 100:.2f} (n={stats[k][2]})  "
                     if stats[k] else f"{name} —  ")
        ok = None
        if stats[0] and stats[2]:
            diff = stats[0][0] - stats[2][0]
            se = float(np.hypot(stats[0][1], stats[2][1]))
            mono = stats[1] is not None and stats[0][0] > stats[1][0] > stats[2][0]
            ok = bool(diff > se and mono)
            line += f"| low-high={diff * 100:+.2f}%±{se * 100:.2f} mono={'Y' if mono else 'N'} -> {'passes' if ok else 'fails'}"
        g2_pass[sym] = ok
        print(line)

    n_eff_1m = round(pooled_n_1m / OVERLAP["1m"])
    d1m = np.array(pooled["1m"]["d_brier"])
    g1 = bool(len(d1m) > 10 and float(np.mean(d1m)) < -_se(d1m, OVERLAP["1m"]))
    print("\n" + "=" * 92)
    print("PRE-REGISTERED VERDICT (docs/PHASE_D2_PLAN.md §gates):")
    print(f"  P0 power: pooled 1m n_eff ~{n_eff_1m} (rule: <{P0_MIN_NEFF} -> INSUFFICIENT-N)")
    if n_eff_1m < P0_MIN_NEFF:
        print("  >>> INSUFFICIENT-N — archive collecting (D2a); re-run when the "
              "curve vintage archive matures. No claim either direction. <<<")
        return
    both_g2 = all(g2_pass.get(s) for s in SYMBOLS)
    print(f"  G1 (carry beats drift, pooled 1m Brier): {'YES' if g1 else 'NO'}")
    print(f"  G2 (monotone terciles, both symbols): {'YES' if both_g2 else 'NO'}")
    if g1 and both_g2:
        print("  >>> PASS — carry carries signal; scope feature integration (own gate) <<<")
    else:
        print("  >>> FAIL/PARTIAL — recorded; D2a archive keeps collecting toward the "
              "full-fidelity re-run (gate unchanged) <<<")


if __name__ == "__main__":
    asyncio.run(main())
