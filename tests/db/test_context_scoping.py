"""Phase 31a.0 — symbol-scoped backtest context (real DB).

The landmine lock: CFTC releases every market on the same Friday, so before
31a.0 the backtest's `_cot_as_of` "two most recent rows" query mixed
DIFFERENT commodities' managed-money nets whenever release dates collide —
which is every week on a multi-symbol table. This proves, against real SQL on
a migrated database, that:

- `_cot_as_of` computes mm_net_delta within ONE market even when another
  market's rows collide on release_date (fail-without/pass-with: remove the
  market filter from the query and the colliding decoy rows produce a
  cross-commodity delta here);
- `_storage_as_of` serves the NG national-storage table to NG only — every
  other symbol gets None, never NG storage dressed up as its own fundamental.

Mirrors the tests/db conventions (testcontainer via conftest.migrated_url);
uses 1990s dates + throwaway market codes so the shared session DB's seeded
2020s rows can never satisfy the `<= as_of` gates.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, time

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.models.orm.cot import COTReport
from apps.api.models.orm.eia import EIAStorageReport
from apps.api.services.backtest import _cot_as_of, _storage_as_of

_NG_CODE = "T31NG"
_CL_CODE = "T31CL"
_AS_OF = datetime.combine(date(1990, 4, 14), time(23, 59, 59))


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


def _cot(release: date, code: str, mm_long: int, mm_short: int) -> COTReport:
    return COTReport(
        report_date=release,
        release_date=release,
        contract_market_name=f"TEST MARKET {code}",
        cftc_contract_market_code=code,
        managed_money_long=mm_long,
        managed_money_short=mm_short,
        open_interest_total=1_000_000,
    )


@pytest.mark.asyncio
async def test_cot_as_of_is_market_scoped_on_real_sql(migrated_url):
    async with _db(migrated_url) as session:
        try:
            # Two markets, colliding weekly release dates — the real-world
            # shape of a multi-symbol COT table.
            session.add_all(
                [
                    _cot(date(1990, 4, 6), _NG_CODE, 100_000, 0),
                    _cot(date(1990, 4, 6), _CL_CODE, 500_000, 0),
                    _cot(date(1990, 4, 13), _NG_CODE, 120_000, 0),
                    _cot(date(1990, 4, 13), _CL_CODE, 900_000, 0),
                ]
            )
            await session.flush()

            ng = await _cot_as_of(session, _AS_OF, _NG_CODE)
            cl = await _cot_as_of(session, _AS_OF, _CL_CODE)
            # Same-market WoW deltas — a cross-market pair would produce
            # e.g. 120k - 900k = -780k here.
            assert ng == {"mm_net_delta": 20_000.0}
            assert cl == {"mm_net_delta": 400_000.0}
        finally:
            await session.execute(
                delete(COTReport).where(
                    COTReport.cftc_contract_market_code.in_([_NG_CODE, _CL_CODE])
                )
            )
            await session.commit()


@pytest.mark.asyncio
async def test_storage_as_of_is_ng_only_on_real_sql(migrated_url):
    async with _db(migrated_url) as session:
        try:
            session.add(
                EIAStorageReport(
                    report_date=date(1990, 4, 9),
                    week_ending=date(1990, 4, 3),
                    total_lower_48_bcf=1500.0,
                    net_change_bcf=20.0,
                    surprise_bcf=-3.0,
                    source="test",
                )
            )
            await session.flush()

            ng = await _storage_as_of(session, _AS_OF, "NG")
            assert ng is not None
            assert ng["delta_vs_consensus"] == -3.0
            # NG national storage must never masquerade as another symbol's
            # fundamental (the pre-31a.0 contamination).
            for symbol in ("CL", "HO", "RB", "GC", "SI", "ES", "ZN"):
                assert await _storage_as_of(session, _AS_OF, symbol) is None
        finally:
            await session.execute(
                delete(EIAStorageReport).where(
                    EIAStorageReport.report_date == date(1990, 4, 9)
                )
            )
            await session.commit()
