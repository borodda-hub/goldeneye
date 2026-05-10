"""Verifies that alembic upgrade head succeeds and all expected tables exist."""
import pytest


EXPECTED_RELATIONAL = [
    "instruments", "contracts", "eia_storage_reports", "cot_reports",
    "news_events", "model_forecasts", "scenario_runs", "user_decision_journals",
    "paper_trades", "alerts", "adapter_runs",
]
EXPECTED_HYPERTABLES = [
    "price_bars", "tick_data", "futures_curve_snapshots",
    "weather_observations", "weather_forecasts",
]


@pytest.mark.asyncio
async def test_relational_tables_exist(migrated_url):
    import asyncpg
    conn = await asyncpg.connect(migrated_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        existing = {r["tablename"] for r in rows}
        for table in EXPECTED_RELATIONAL + EXPECTED_HYPERTABLES:
            assert table in existing, f"Table {table!r} not found after migration"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_hypertables_registered(migrated_url):
    import asyncpg
    conn = await asyncpg.connect(migrated_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch("SELECT hypertable_name FROM timescaledb_information.hypertables")
        hypertables = {r["hypertable_name"] for r in rows}
        for ht in EXPECTED_HYPERTABLES:
            assert ht in hypertables, f"Hypertable {ht!r} not registered"
    finally:
        await conn.close()
