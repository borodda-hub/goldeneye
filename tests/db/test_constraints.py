"""Tests for generated columns and check constraints."""
import pytest
import asyncpg


@pytest.fixture(scope="module")
def db_url(migrated_url):
    return migrated_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.mark.asyncio
async def test_cot_managed_money_net_generated(db_url):
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            INSERT INTO instruments (symbol, name, exchange, unit, contract_size, tick_size)
            VALUES ('NG_TEST', 'Test NG', 'NYMEX', 'MMBtu', 10000, 0.001)
        """)
        await conn.execute("""
            INSERT INTO cot_reports (report_date, release_date, contract_market_name,
                cftc_contract_market_code, open_interest_total,
                managed_money_long, managed_money_short)
            VALUES ('2024-01-02', '2024-01-05', 'TEST MARKET', 'TEST_CODE', 1000000, 250000, 100000)
        """)
        net = await conn.fetchval(
            "SELECT managed_money_net FROM cot_reports WHERE contract_market_name = 'TEST MARKET'"
        )
        assert net == 150000, f"Expected 150000, got {net}"
    finally:
        await conn.execute("DELETE FROM cot_reports WHERE contract_market_name = 'TEST MARKET'")
        await conn.execute("DELETE FROM instruments WHERE symbol = 'NG_TEST'")
        await conn.close()


@pytest.mark.asyncio
async def test_journal_confidence_check_constraint(db_url):
    conn = await asyncpg.connect(db_url)
    try:
        instr_id = await conn.fetchval("""
            INSERT INTO instruments (symbol, name, exchange, unit, contract_size, tick_size)
            VALUES ('NG_CK', 'Check NG', 'NYMEX', 'MMBtu', 10000, 0.001)
            RETURNING id
        """)
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute("""
                INSERT INTO user_decision_journals (instrument_id, hypothesis, confidence_pct)
                VALUES ($1, 'Test hypothesis', -1)
            """, instr_id)
    finally:
        await conn.execute("DELETE FROM instruments WHERE symbol = 'NG_CK'")
        await conn.close()
