"""Phase 31a — COT/EIA upsert repos against real Postgres.

The tables' UNIQUE constraints are the backfill's idempotency keys. Proves on
real SQL that a re-run updates in place (no duplicates) — including the
intended overwrite of same-key mock rows by real history — for both conflict
shapes: (report_date, contract_market_name) on cot_reports and (report_date)
on eia_storage_reports.

Uses 1990s dates + throwaway market names so the shared session DB's seeded
2020s rows can't collide.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.models.orm.cot import COTReport
from apps.api.models.orm.eia import EIAStorageReport
from apps.api.repos import cot as cot_repo
from apps.api.repos import eia as eia_repo

_MARKET = "T31A UPSERT MARKET"


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


def _cot_row(report_date: date, mm_long: int, source: str) -> dict:
    return {
        "report_date": report_date,
        "release_date": report_date,
        "contract_market_name": _MARKET,
        "cftc_contract_market_code": "T31A",
        "managed_money_long": mm_long,
        "managed_money_short": 0,
        "open_interest_total": 1_000_000,
        "source": source,
    }


def _eia_row(report_date: date, level: float, source: str) -> dict:
    return {
        "report_date": report_date,
        "week_ending": report_date,
        "total_lower_48_bcf": level,
        "net_change_bcf": 10.0,
        "consensus_estimate": None,
        "surprise_bcf": None,
        "source": source,
    }


@pytest.mark.asyncio
async def test_cot_upsert_idempotent_and_overwrites(migrated_url):
    async with _db(migrated_url) as session:
        try:
            first = [_cot_row(date(1991, 4, 2), 100_000, "mock"), _cot_row(date(1991, 4, 9), 110_000, "mock")]
            await cot_repo.upsert_many(session, first)
            await session.commit()

            # Re-run with one changed value + one new week — real over mock.
            second = [
                _cot_row(date(1991, 4, 2), 123_456, "cftc"),
                _cot_row(date(1991, 4, 9), 110_000, "cftc"),
                _cot_row(date(1991, 4, 16), 120_000, "cftc"),
            ]
            await cot_repo.upsert_many(session, second)
            await session.commit()

            rows = (
                (
                    await session.execute(
                        select(COTReport)
                        .where(COTReport.contract_market_name == _MARKET)
                        .order_by(COTReport.report_date)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 3  # no duplicates on the conflict key
            assert rows[0].managed_money_long == 123_456  # updated in place
            assert all(r.source == "cftc" for r in rows[:2])  # mock overwritten
            # GENERATED managed_money_net recomputed from the upserted values.
            assert rows[0].managed_money_net == 123_456
        finally:
            await session.execute(delete(COTReport).where(COTReport.contract_market_name == _MARKET))
            await session.commit()


@pytest.mark.asyncio
async def test_provenance_observation_reads_db_truth(migrated_url):
    """31d: the LLM caveat's clause derives from OBSERVED rows. Fresh
    real-sourced rows → real; remove them (leaving stale/mock seed data) →
    not-real. Real SQL, the same get_latest path production observes."""
    from datetime import date as _date
    from datetime import timedelta as _td

    from apps.api.services.feature_provenance import observe_feature_provenance

    today = _date.today()
    async with _db(migrated_url) as session:
        try:
            await cot_repo.upsert_many(
                session, [_cot_row(today - _td(days=3), 100_000, "cftc")]
            )
            await eia_repo.upsert_many(
                session, [_eia_row(today - _td(days=2), 3000.0, "eia")]
            )
            await session.commit()
            prov = await observe_feature_provenance(session)
            assert prov.cot_real is True
            assert prov.storage_real is True
        finally:
            await session.execute(
                delete(COTReport).where(COTReport.contract_market_name == _MARKET)
            )
            await session.execute(
                delete(EIAStorageReport).where(
                    EIAStorageReport.report_date == today - _td(days=2)
                )
            )
            await session.commit()
        # With the fresh real rows gone, whatever remains (seeded mock, stale
        # dates) must NOT read as real.
        prov = await observe_feature_provenance(session)
        assert prov.cot_real is False
        assert prov.storage_real is False


@pytest.mark.asyncio
async def test_eia_upsert_idempotent_and_overwrites(migrated_url):
    async with _db(migrated_url) as session:
        try:
            await eia_repo.upsert_many(session, [_eia_row(date(1991, 4, 4), 1500.0, "mock")])
            await session.commit()
            await eia_repo.upsert_many(
                session,
                [_eia_row(date(1991, 4, 4), 1512.5, "eia"), _eia_row(date(1991, 4, 11), 1520.0, "eia")],
            )
            await session.commit()

            rows = (
                (
                    await session.execute(
                        select(EIAStorageReport)
                        .where(EIAStorageReport.report_date >= date(1991, 1, 1), EIAStorageReport.report_date < date(1992, 1, 1))
                        .order_by(EIAStorageReport.report_date)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 2
            assert float(rows[0].total_lower_48_bcf) == 1512.5
            assert rows[0].source == "eia"
        finally:
            await session.execute(
                delete(EIAStorageReport).where(
                    EIAStorageReport.report_date >= date(1991, 1, 1),
                    EIAStorageReport.report_date < date(1992, 1, 1),
                )
            )
            await session.commit()
