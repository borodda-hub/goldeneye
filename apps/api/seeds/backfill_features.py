"""Backfill real COT + EIA NG storage feature history (Phase 31a).

Run with:  python -m seeds.backfill_features [--symbols NG CL ...] [--years 10]

Fetches real weekly history through the REAL adapters' paginated range paths
(CFTC PRE Socrata — no key; EIA Open Data v2 — needs EIA_API_KEY) and upserts
it into `cot_reports` / `eia_storage_reports`. The tables' UNIQUE constraints
are the idempotency keys: a re-run refreshes values, never duplicates, and
real rows overwrite same-key mock rows from the demo seed.

Scope (docs/PHASE_31_PLAN.md §31a): COT for the six full-tier commodities +
EIA weekly NG national storage. Petroleum stocks are deliberately NOT
backfilled (the table is NG-shaped; the petroleum adapter's range method is
protocol-parity only).

Manual/cron, NOT CI (live network + EIA_API_KEY) — same posture as
`backfill_prices` / the `validate_*_real` diagnostics. Writes to whatever
DATABASE_URL points at; promoting real data to production is a deliberate,
separate step.

Idempotency is reported as net-new = table rowcount delta (an ON CONFLICT DO
UPDATE rowcount counts updates too, so it can't distinguish new from
refreshed).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_SYMBOLS = ["NG", "CL", "HO", "RB", "GC", "SI"]
DEFAULT_YEARS = 10


async def go(symbols: list[str], years: int) -> None:
    from sqlalchemy import delete, func, select

    from apps.api.adapters.energy.eia import EIAAdapter
    from apps.api.adapters.positioning.cftc import MARKETS, CFTCAdapter
    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.cot import COTReport
    from apps.api.models.orm.eia import EIAStorageReport
    from apps.api.repos import cot as cot_repo
    from apps.api.repos import eia as eia_repo
    from apps.api.src.settings import settings

    end = date.today()
    start = end - timedelta(days=round(years * 365.25))
    print(f"Backfilling {start} -> {end} ({years}y) for {' '.join(symbols)}\n")

    async with get_session_factory()() as session:

        async def table_count(model) -> int:
            return (await session.execute(select(func.count()).select_from(model))).scalar_one()

        # ── COT (CFTC PRE Socrata, keyless) ───────────────────────────────
        cot_before = await table_count(COTReport)
        for symbol in symbols:
            if symbol not in MARKETS:
                print(f"COT {symbol}: no CFTC market registered — skipped")
                continue
            code = MARKETS[symbol].contract_code
            adapter = CFTCAdapter(symbol)
            try:
                rows = await adapter.get_cot_reports_range(start, end)
            except Exception as exc:
                print(f"COT {symbol}: fetch FAILED — {exc}")
                continue
            if not rows:
                print(f"COT {symbol}: fetched 0 reports — nothing changed")
                continue
            # Replace-mock (the price_backfill pattern): the upsert key is
            # (report_date, contract_market_name) but Socrata's names have
            # CHANGED over time, so mock rows (long seed names) would sit
            # ALONGSIDE real rows (current short names) for the same week —
            # and _cot_as_of filters by market CODE, so a mock+real pair for
            # one week would poison mm_net_delta. Purge non-CFTC-sourced rows
            # for this market only after a successful non-empty fetch.
            removed = await session.execute(
                delete(COTReport).where(
                    COTReport.cftc_contract_market_code == code,
                    COTReport.source != "cftc",
                )
            )
            affected = await cot_repo.upsert_many(session, rows)
            await session.commit()
            # Loud dup guard: one row per (report_date) within this market.
            # A future Socrata rename would silently duplicate weeks again —
            # fail the run rather than hand 31b a poisoned table.
            dup = (
                await session.execute(
                    select(COTReport.report_date)
                    .where(COTReport.cftc_contract_market_code == code)
                    .group_by(COTReport.report_date)
                    .having(func.count() > 1)
                )
            ).all()
            if dup:
                raise RuntimeError(
                    f"COT {symbol}: {len(dup)} duplicated report_dates within "
                    f"market {code} (name churn?) — table is poisoned, fix "
                    f"before running backtests"
                )
            print(
                f"COT {symbol}: fetched {len(rows)} weekly reports "
                f"({rows[-1]['report_date']} -> {rows[0]['report_date']}), "
                f"upserted {affected}, replaced {removed.rowcount or 0} mock rows"
            )
        cot_after = await table_count(COTReport)
        print(f"COT net-new rows: {cot_after - cot_before} (table {cot_before} -> {cot_after})\n")

        # ── EIA NG national storage (needs EIA_API_KEY) ───────────────────
        if "NG" not in symbols:
            print("EIA storage: NG not in symbols — skipped")
            return
        if not settings.eia_api_key:
            print("EIA storage: EIA_API_KEY not set — skipped")
            return
        eia_before = await table_count(EIAStorageReport)
        try:
            storage_rows = await EIAAdapter().get_storage_reports_range(start, end)
        except Exception as exc:
            print(f"EIA storage: fetch FAILED — {exc}")
            return
        affected = await eia_repo.upsert_many(session, storage_rows)
        await session.commit()
        span = (
            f"{storage_rows[-1]['week_ending']} -> {storage_rows[0]['week_ending']}"
            if storage_rows
            else "empty"
        )
        eia_after = await table_count(EIAStorageReport)
        print(
            f"EIA storage NG: fetched {len(storage_rows)} weekly reports ({span}), "
            f"upserted {affected}"
        )
        print(f"EIA net-new rows: {eia_after - eia_before} (table {eia_before} -> {eia_after})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    args = parser.parse_args()
    asyncio.run(go([s.upper() for s in args.symbols], args.years))
