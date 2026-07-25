"""Phase D4 — storage-day event-window abstention probe (pre-registered).

Conditional on a LARGE EIA storage surprise (vs the 31a.0 walk-forward
seasonal norm), is the subsequent NG move predictable? Gates locked in
docs/PHASE_D4_PLAN.md BEFORE the first run — not tunable post-hoc.

Events = real publication Thursdays from `eia_storage_reports` (14y, 31a).
Reaction window (G0 sanity) = Wed→Thu close. Tradeable window (the gate) =
Thu close → next Thu close, entered strictly after the release. Extreme =
outside the middle tercile of the walk-forward |surprise| distribution;
weekly events + 1w horizon → non-overlapping, n_eff = n.

Run:  uv run --directory apps/api python -m seeds.validate_d4_storage_event
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

from apps.api.adapters._http import AdapterHTTPClient  # noqa: E402
from apps.api.adapters.market.yahoo_delayed import (  # noqa: E402
    _HEADERS,
    YAHOO_BASE_URL,
    _parse_chart,
)
from apps.api.services.storage_features import delta_vs_seasonal_norm  # noqa: E402

P0_MIN_EXTREME = 200
BUCKET_WARMUP = 52
FWD_CAP = 7


async def _ng_closes() -> tuple[list[date], list[float]]:
    client = AdapterHTTPClient(adapter_name="validate.d4_storage_event")
    try:
        resp = await client.get(
            YAHOO_BASE_URL + "NG=F",
            params={"interval": "1d", "range": "15y", "includePrePost": "false"},
            headers=_HEADERS,
        )
        bars = _parse_chart(resp.json(), "NG=F", "1d")
    finally:
        await client.close()  # type: ignore[no-untyped-call]
    bars.sort(key=lambda b: b["ts"])
    dates = [b["ts"].date() for b in bars if b["close"] > 0]
    closes = [float(b["close"]) for b in bars if b["close"] > 0]
    return dates, closes


async def _storage_rows() -> list[tuple[date, date, float]]:
    """(report_date, week_ending, net_change) for real rows, oldest first."""
    from sqlalchemy import select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.eia import EIAStorageReport

    async with get_session_factory()() as session:
        rows = (
            await session.execute(
                select(
                    EIAStorageReport.report_date,
                    EIAStorageReport.week_ending,
                    EIAStorageReport.net_change_bcf,
                )
                .where(EIAStorageReport.source == "eia")
                .order_by(EIAStorageReport.report_date)
            )
        ).all()
    return [
        (r, w, float(n)) for r, w, n in rows if n is not None and r is not None
    ]


def _close_index_on_or_before(dates: list[date], d: date) -> int | None:
    i = bisect_left(dates, d)
    if i < len(dates) and dates[i] == d:
        return i
    return i - 1 if i > 0 else None


def _fwd_ret(dates: list[date], closes: list[float], t: int, hd: int) -> float | None:
    target = dates[t] + timedelta(days=hd)
    u = bisect_left(dates, target)
    if u >= len(dates) or dates[u] > target + timedelta(days=FWD_CAP):
        return None
    return closes[u] / closes[t] - 1.0


async def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

    dates, closes = await _ng_closes()
    storage = await _storage_rows()
    print(f"NG closes: {len(closes)} ({dates[0]} -> {dates[-1]}); "
          f"real storage rows: {len(storage)}")

    # Walk-forward surprise per event: actual net change vs the same-week 5y
    # norm computed from strictly-prior rows (the 31a.0 helper, unchanged).
    events = []  # (report_date, surprise)
    history: list[tuple[date, float]] = []
    for report_date, week_ending, net_change in storage:
        s = delta_vs_seasonal_norm(week_ending, net_change, history)
        history.append((week_ending, net_change))
        if s is not None:
            events.append((report_date, float(s)))
    print(f"events with computable surprise: {len(events)}")

    rows = []  # (s, reaction, fwd_1w, drift_hit_dir)
    for report_date, s in events:
        t = _close_index_on_or_before(dates, report_date)
        if t is None or dates[t] != report_date:
            continue  # release day must itself be a trading day close
        if t < 101:
            continue
        reaction = closes[t] / closes[t - 1] - 1.0
        fwd = _fwd_ret(dates, closes, t, 7)
        if fwd is None:
            continue
        rets = np.diff(np.log(closes[t - 100 : t + 1]))
        drift_up = float(np.mean(rets > 0)) > 0.5
        rows.append((s, reaction, fwd, drift_up))
    print(f"scored events: {len(rows)}")

    s_arr = np.array([r[0] for r in rows])
    react = np.array([r[1] for r in rows])
    fwd = np.array([r[2] for r in rows])
    drift_up = np.array([r[3] for r in rows])

    # G0 — does the surprise move price on release day (classic sign: bigger
    # build than normal -> down)?
    g0_corr = float(np.corrcoef(s_arr, react)[0, 1])
    print(f"\nG0 sanity: corr(surprise, release-day move) = {g0_corr:+.3f} "
          f"({'classic sign' if g0_corr < 0 else 'PREMISE ABSENT — wrong/no sign'})")

    # Walk-forward extreme flag: |s| outside the middle tercile of prior |s|.
    extreme = np.zeros(len(rows), dtype=bool)
    for i in range(len(rows)):
        past = np.abs(s_arr[:i])
        if len(past) < BUCKET_WARMUP:
            continue
        lo, hi = np.percentile(past, [33.0, 67.0])
        extreme[i] = abs(s_arr[i]) >= hi
    ex = extreme
    n_ex = int(ex.sum())

    # G1 — the abstention claim on extreme events (1w post-event direction).
    rule_bull = s_arr < 0
    y_up = fwd > 0
    hits = (rule_bull == y_up)[ex]
    p = float(np.mean(hits)) if n_ex else float("nan")
    se = float(np.sqrt(p * (1 - p) / n_ex)) if n_ex else float("nan")
    base = float(np.mean(y_up[ex])) if n_ex else float("nan")
    base_best = max(base, 1 - base)
    drift_hits = (drift_up == y_up)[ex]
    drift_acc = float(np.mean(drift_hits)) if n_ex else float("nan")
    bar = max(0.5, base_best, drift_acc)
    print(f"\nG1 (extreme events only): n={n_ex} (n_eff=n, non-overlapping)")
    print(f"  rule hit = {p * 100:.1f}% ± {se * 100:.1f}  vs bar = max(50, "
          f"const {base_best * 100:.1f}, drift {drift_acc * 100:.1f}) = {bar * 100:.1f}")
    g1 = bool(n_ex and (p - se) > bar)
    print(f"  -> {'CLEARS the bar by >1 SE' if g1 else 'does NOT clear the bar'}")

    # G2 — dose-response: mean 1w return across walk-forward surprise quintiles.
    q_assign = np.full(len(rows), -1)
    for i in range(len(rows)):
        past = s_arr[:i]
        if len(past) < BUCKET_WARMUP:
            continue
        qs = np.percentile(past, [20, 40, 60, 80])
        q_assign[i] = int(np.searchsorted(qs, s_arr[i]))
    print("\nG2 quintiles (surprise low->high) -> mean 1w post-event return:")
    means = []
    for q in range(5):
        x = fwd[q_assign == q]
        if len(x) >= 20:
            m, s_e = float(np.mean(x)), float(np.std(x, ddof=1) / np.sqrt(len(x)))
            means.append(m)
            print(f"  q{q + 1}: {m * 100:+.2f}% ± {s_e * 100:.2f} (n={len(x)})")
        else:
            means.append(None)
            print(f"  q{q + 1}: n<20")
    mono = all(
        means[i] is not None and means[i + 1] is not None and means[i] > means[i + 1]
        for i in range(4)
    )
    g2 = False
    if means[0] is not None and means[-1] is not None:
        x0, x4 = fwd[q_assign == 0], fwd[q_assign == 4]
        diff = float(np.mean(x0) - np.mean(x4))
        dse = float(
            np.hypot(np.std(x0, ddof=1) / np.sqrt(len(x0)), np.std(x4, ddof=1) / np.sqrt(len(x4)))
        )
        g2 = bool(diff > dse and mono)
        print(f"  q1-q5 = {diff * 100:+.2f}% ± {dse * 100:.2f}; strictly monotone="
              f"{'Y' if mono else 'N'} -> {'passes' if g2 else 'fails'}")

    print("\n" + "=" * 88)
    print("PRE-REGISTERED VERDICT (docs/PHASE_D4_PLAN.md §gates):")
    if n_ex < P0_MIN_EXTREME:
        print(f"  P0: extreme n={n_ex} < {P0_MIN_EXTREME} -> INSUFFICIENT-N")
        return
    print(f"  P0 ok (extreme n={n_ex})   G1: {'YES' if g1 else 'NO'}   G2: {'YES' if g2 else 'NO'}")
    if g1 and g2:
        print("  >>> PASS — scope the abstaining view (own phase, S6-framed) <<<")
    else:
        print("  >>> FAIL/PARTIAL — recorded; re-entry only via new data, gate unchanged <<<")


if __name__ == "__main__":
    asyncio.run(main())
