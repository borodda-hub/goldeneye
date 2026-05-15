"""
Demo seed orchestrator.
Usage: python -m apps.api.seeds.demo [--fresh]
  --fresh: drop all generated rows before re-seeding (fixture rows are kept)

Steps:
1. Load JSON fixtures (if not already loaded) — calls load_fixtures.load_all()
2. Run price_generator.generate() → bulk insert price_bars and futures_curve_snapshots
3. Run storage_generator.generate() → bulk insert eia_storage_reports
4. Run cot_generator.generate() → bulk insert cot_reports
5. Run weather_generator.generate() → bulk insert weather_observations + weather_forecasts
6. Run validate.run_checks(session)

For step 2, look up contract_ids by contract_code from the DB.
For step 3-5, no FK lookups needed (no FK columns on those tables).

--fresh mode: DELETE FROM price_bars, futures_curve_snapshots, eia_storage_reports,
              cot_reports, weather_observations, weather_forecasts before re-seeding.
              Does NOT delete fixture tables (instruments, contracts, news_events, etc.)

Use bulk inserts via SQLAlchemy Core insert() for performance.
Use asyncio.run(main()) at the bottom.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def main(fresh: bool = False) -> None:
    from sqlalchemy import insert, select

    from apps.api.db.base import Base
    from apps.api.db.session import get_session_factory
    import apps.api.models.orm.instruments   # noqa: F401
    import apps.api.models.orm.contracts     # noqa: F401
    import apps.api.models.orm.prices        # noqa: F401
    import apps.api.models.orm.eia           # noqa: F401
    import apps.api.models.orm.cot           # noqa: F401
    import apps.api.models.orm.weather       # noqa: F401
    import apps.api.models.orm.journal       # noqa: F401
    import apps.api.models.orm.paper         # noqa: F401
    import apps.api.models.orm.forecasts     # noqa: F401

    from apps.api.seeds import load_fixtures, price_generator, storage_generator
    from apps.api.seeds import cot_generator, weather_generator, validate
    from apps.api.seeds import example_journal_and_trades, example_forecasts

    meta = Base.metadata
    price_bars_t          = meta.tables["price_bars"]
    curve_snapshots_t     = meta.tables["futures_curve_snapshots"]
    eia_t                 = meta.tables["eia_storage_reports"]
    cot_t                 = meta.tables["cot_reports"]
    weather_obs_t         = meta.tables["weather_observations"]
    weather_fcast_t       = meta.tables["weather_forecasts"]
    instruments_t         = meta.tables["instruments"]
    contracts_t           = meta.tables["contracts"]

    session_factory = get_session_factory()

    # ── Step 1: Load fixtures ───────────────────────────────────────────────
    print("step 1: loading fixtures …")
    await load_fixtures.load_all()
    print("step 1: fixtures loaded")

    async with session_factory() as session:
        async with session.begin():

            # ── Fresh mode: delete generated rows ──────────────────────────
            if fresh:
                print("--fresh: deleting generated rows …")
                for tbl in [
                    weather_fcast_t, weather_obs_t, cot_t,
                    eia_t, price_bars_t, curve_snapshots_t,
                ]:
                    await session.execute(tbl.delete())
                print("--fresh: done")

            # ── Look up contract and instrument IDs ─────────────────────────
            contract_rows = (await session.execute(select(contracts_t))).fetchall()
            contract_id_by_code: dict[str, Any] = {
                row.contract_code: row.id for row in contract_rows
            }

            instrument_rows = (await session.execute(select(instruments_t))).fetchall()
            instrument_id_by_symbol: dict[str, Any] = {
                row.symbol: row.id for row in instrument_rows
            }

            # ── Step 2: Price bars and curve snapshots ──────────────────────
            print("step 2: generating price bars …")
            price_data = price_generator.generate()

            # Map bars: replace contract_code with contract_id
            price_bar_rows = []
            for bar in price_data["bars"]:
                code = bar["contract_code"]
                contract_id = contract_id_by_code.get(code)
                if contract_id is None:
                    print(f"  warning: contract {code!r} not found in DB, skipping bar")
                    continue
                price_bar_rows.append({
                    "ts": bar["ts"],
                    "contract_id": contract_id,
                    "resolution": bar["resolution"],
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                    "source": bar["source"],
                })

            # Bulk insert in chunks
            _CHUNK = 2000
            for i in range(0, len(price_bar_rows), _CHUNK):
                chunk = price_bar_rows[i:i + _CHUNK]
                await session.execute(
                    insert(price_bars_t).values(chunk)
                )
            print(f"  inserted {len(price_bar_rows)} price bars")

            # Curve snapshots: replace instrument_symbol with instrument_id
            curve_rows = []
            for snap in price_data["snapshots"]:
                sym = snap["instrument_symbol"]
                instr_id = instrument_id_by_symbol.get(sym)
                if instr_id is None:
                    print(f"  warning: instrument {sym!r} not found in DB, skipping snapshot")
                    continue
                curve_rows.append({
                    "ts": snap["ts"],
                    "instrument_id": instr_id,
                    "curve": snap["curve"],
                })

            for i in range(0, len(curve_rows), _CHUNK):
                chunk = curve_rows[i:i + _CHUNK]
                await session.execute(
                    insert(curve_snapshots_t).values(chunk)
                )
            print(f"  inserted {len(curve_rows)} curve snapshots")

            # ── Step 3: EIA storage reports ─────────────────────────────────
            print("step 3: generating EIA storage reports …")
            eia_rows_raw = storage_generator.generate()
            eia_rows = [
                {k: v for k, v in row.items()}
                for row in eia_rows_raw
            ]
            for i in range(0, len(eia_rows), _CHUNK):
                await session.execute(insert(eia_t).values(eia_rows[i:i + _CHUNK]))
            print(f"  inserted {len(eia_rows)} EIA reports")

            # ── Step 4: COT reports ─────────────────────────────────────────
            print("step 4: generating COT reports …")
            cot_rows_raw = cot_generator.generate()
            # Exclude managed_money_net (DB-computed generated column)
            cot_rows = [
                {k: v for k, v in row.items() if k != "managed_money_net"}
                for row in cot_rows_raw
            ]
            for i in range(0, len(cot_rows), _CHUNK):
                await session.execute(insert(cot_t).values(cot_rows[i:i + _CHUNK]))
            print(f"  inserted {len(cot_rows)} COT reports")

            # ── Step 5: Weather ─────────────────────────────────────────────
            print("step 5: generating weather data …")
            weather_data = weather_generator.generate()

            obs_rows = weather_data["observations"]
            for i in range(0, len(obs_rows), _CHUNK):
                await session.execute(insert(weather_obs_t).values(obs_rows[i:i + _CHUNK]))
            print(f"  inserted {len(obs_rows)} weather observations")

            fcast_rows = weather_data["forecasts"]
            for i in range(0, len(fcast_rows), _CHUNK):
                await session.execute(insert(weather_fcast_t).values(fcast_rows[i:i + _CHUNK]))
            print(f"  inserted {len(fcast_rows)} weather forecasts")

            # ── Step 6: Example journal entries + paper trades ──────────────
            print("step 6: seeding example journal entries + paper trades …")
            j_count, t_count = await example_journal_and_trades.seed_examples(session)
            if j_count == 0 and t_count == 0:
                print("  examples already present — skipped")
            else:
                print(f"  inserted {j_count} journal entries, {t_count} paper trades")

            # ── Step 6b: Example model_forecasts for signal-lab history ─────
            print("step 6b: seeding model_forecasts for the signal lab history …")
            total = 0
            for sym in ("NG", "CL", "HO", "RB", "GC", "SI"):
                n = await example_forecasts.seed_forecasts(session, symbol=sym)
                total += n
                if n:
                    print(f"  {sym}: inserted {n} forecast rows")
            if total == 0:
                print("  forecasts already present — skipped")

        # ── Step 7: Validate ────────────────────────────────────────────────
        print("step 7: running validation checks …")
        try:
            await validate.run_checks_async(session)
            print("step 7: all checks passed")
        except AssertionError as e:
            print(f"step 7: FAILED — {e}", file=sys.stderr)
            sys.exit(1)

    print("demo seed complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Goldeneye demo seed")
    parser.add_argument("--fresh", action="store_true", help="Delete generated rows before seeding")
    args = parser.parse_args()
    asyncio.run(main(fresh=args.fresh))
