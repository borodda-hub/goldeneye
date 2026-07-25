"""Phase D2a — futures-curve vintage archive (real DB): immutability +
labeled idempotent tick leg. Mirrors tests/db/test_weather_vintages.py."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.models.orm.curve_vintages import FuturesCurveVintage
from apps.api.repos import curve_vintages as cv_repo
from apps.api.services.feature_refresh import _archive_curve_vintage


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
def mock_market(monkeypatch):
    """Hermeticity pin: a dev .env may configure a REAL market adapter — the
    tick-leg test must never hit the network. Force mock + clear the
    registry's lru caches on both sides."""
    from apps.api.adapters import registry
    from apps.api.src.settings import settings

    registry.get_market.cache_clear()
    monkeypatch.setattr(settings, "adapter_market", "mock")
    yield
    registry.get_market.cache_clear()


@pytest.mark.asyncio
async def test_curve_vintages_are_immutable_history(migrated_url):
    v = date(1990, 2, 1)
    row = {
        "vintage_date": v,
        "symbol": "NG",
        "curve": [{"contract_code": "NGH90", "mid_price": 1.5}],
        "source": "test",
    }
    async with _db(migrated_url) as session:
        try:
            assert await cv_repo.insert_vintages(session, [row]) == 1
            await session.commit()
            changed = dict(row, curve=[{"contract_code": "NGH90", "mid_price": 99.0}])
            assert await cv_repo.insert_vintages(session, [changed]) == 0
            await session.commit()
            kept = (
                await session.execute(
                    select(FuturesCurveVintage).where(
                        FuturesCurveVintage.vintage_date == v
                    )
                )
            ).scalar_one()
            assert kept.curve[0]["mid_price"] == 1.5  # original preserved
        finally:
            await session.execute(
                delete(FuturesCurveVintage).where(FuturesCurveVintage.source == "test")
            )
            await session.commit()


@pytest.mark.asyncio
async def test_refresh_tick_curve_leg_labeled_and_idempotent(migrated_url, mock_market):
    today = date.today()
    async with _db(migrated_url) as session:
        try:
            n1 = await _archive_curve_vintage(session)
            await session.commit()
            assert n1 >= 1  # mock market adapter serves at least one curve
            rows = (
                (
                    await session.execute(
                        select(FuturesCurveVintage).where(
                            FuturesCurveVintage.vintage_date == today
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert all(r.source for r in rows)  # every vintage labeled
            assert all(r.curve for r in rows)
            n2 = await _archive_curve_vintage(session)
            await session.commit()
            assert n2 == 0  # idempotent within the day
        finally:
            await session.execute(
                delete(FuturesCurveVintage).where(
                    FuturesCurveVintage.vintage_date == today
                )
            )
            await session.commit()
