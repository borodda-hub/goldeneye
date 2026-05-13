"""Backfill CL daily price bars into price_bars from Yahoo.

Run with:  python -m apps.api.seeds._backfill_cl_prices

Pulls 2 years of 1d bars for every CL contract that has a row in `contracts`,
inserts into `price_bars`. Idempotent at the bar level via the unique
(contract_id, resolution, ts) constraint — uses ON CONFLICT DO NOTHING so
re-runs are safe.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def go() -> None:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from apps.api.adapters.registry import get_market
    from apps.api.db.base import Base
    from apps.api.db.session import get_session_factory
    import apps.api.models.orm.instruments  # noqa: F401
    import apps.api.models.orm.contracts  # noqa: F401
    import apps.api.models.orm.prices  # noqa: F401

    meta = Base.metadata
    instruments_t = meta.tables["instruments"]
    contracts_t = meta.tables["contracts"]
    price_bars_t = meta.tables["price_bars"]

    market = get_market()
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            # Resolve CL instrument id.
            cl_row = (
                await session.execute(
                    select(instruments_t.c.id).where(instruments_t.c.symbol == "CL")
                )
            ).first()
            if cl_row is None:
                print("error: CL instrument not seeded — run load_fixtures first")
                return

            # Pull every CL contract.
            contract_rows = (
                await session.execute(
                    select(contracts_t.c.id, contracts_t.c.contract_code).where(
                        contracts_t.c.instrument_id == cl_row.id
                    )
                )
            ).all()
            if not contract_rows:
                print("error: no CL contracts seeded")
                return

            total_inserted = 0
            now = datetime.utcnow()
            two_years_ago = now - timedelta(days=730)

            for contract_id, contract_code in contract_rows:
                try:
                    bars = await market.get_bars(
                        contract_code, "1d", two_years_ago, now
                    )
                except Exception as exc:
                    print(f"  {contract_code}: fetch failed — {exc}")
                    continue
                if not bars:
                    print(f"  {contract_code}: 0 bars from market")
                    continue

                rows = [
                    {
                        "contract_id": contract_id,
                        "resolution": "1d",
                        "ts": b["ts"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b.get("volume") or 0,
                        "source": "yahoo_delayed",
                    }
                    for b in bars
                ]
                stmt = (
                    pg_insert(price_bars_t)
                    .values(rows)
                    .on_conflict_do_nothing()  # uniq on (contract_id, resolution, ts)
                )
                result = await session.execute(stmt)
                inserted = result.rowcount or 0
                total_inserted += inserted
                print(f"  {contract_code}: inserted {inserted} of {len(rows)} bars")

            print(f"\nBackfill complete — {total_inserted} new CL bars inserted.")


if __name__ == "__main__":
    asyncio.run(go())
