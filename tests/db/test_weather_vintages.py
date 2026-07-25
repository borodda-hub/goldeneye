"""Phase D5 — weather-forecast vintage archive (real DB).

Locks the two properties the archive's honesty depends on:
1. Vintages are immutable: a same-day re-insert is a NO-OP (ON CONFLICT DO
   NOTHING) — a past vintage is never rewritten.
2. The refresh tick's archival leg writes one labeled vintage per region +
   the US aggregate, and is idempotent within a day.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.models.orm.weather_vintages import WeatherForecastVintage
from apps.api.repos import weather_vintages as wv_repo
from apps.api.services.feature_refresh import _archive_weather_vintage


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


def _row(vintage: date, region: str, anomaly: float | None = None) -> dict:
    return {
        "vintage_date": vintage,
        "region": region,
        "forecast": [{"horizon_days": 1, "anomaly_f": 2.5}],
        "national_hdd_anomaly": anomaly,
        "source": "test",
    }


@pytest.mark.asyncio
async def test_vintages_are_immutable_history(migrated_url):
    v = date(1990, 1, 15)
    async with _db(migrated_url) as session:
        try:
            n1 = await wv_repo.insert_vintages(
                session, [_row(v, "northeast"), _row(v, "US", -3.0)]
            )
            await session.commit()
            assert n1 == 2
            # Same-day re-insert with DIFFERENT content must be a no-op —
            # never a rewrite of what was archived.
            changed = _row(v, "northeast")
            changed["forecast"] = [{"horizon_days": 1, "anomaly_f": 99.0}]
            n2 = await wv_repo.insert_vintages(session, [changed])
            await session.commit()
            assert n2 == 0
            kept = (
                await session.execute(
                    select(WeatherForecastVintage).where(
                        WeatherForecastVintage.vintage_date == v,
                        WeatherForecastVintage.region == "northeast",
                    )
                )
            ).scalar_one()
            assert kept.forecast[0]["anomaly_f"] == 2.5  # original preserved
            # Next day appends.
            n3 = await wv_repo.insert_vintages(
                session, [_row(date(1990, 1, 16), "northeast")]
            )
            await session.commit()
            assert n3 == 1
            assert await wv_repo.count_vintage_days(session, source="test") == 2
        finally:
            await session.execute(
                delete(WeatherForecastVintage).where(
                    WeatherForecastVintage.source == "test"
                )
            )
            await session.commit()


@pytest.mark.asyncio
async def test_refresh_tick_archival_leg_writes_labeled_vintage(migrated_url):
    """One labeled row per region + the US aggregate; same-day re-run
    inserts 0 (idempotent). Uses the configured (mock) weather adapter —
    no network."""
    today = date.today()
    async with _db(migrated_url) as session:
        try:
            n1 = await _archive_weather_vintage(session)
            await session.commit()
            assert n1 >= 2  # ≥1 region + the US aggregate
            rows = (
                (
                    await session.execute(
                        select(WeatherForecastVintage).where(
                            WeatherForecastVintage.vintage_date == today
                        )
                    )
                )
                .scalars()
                .all()
            )
            regions = {r.region for r in rows}
            assert "US" in regions
            us = next(r for r in rows if r.region == "US")
            assert us.national_hdd_anomaly is not None
            assert all(r.source for r in rows)  # every vintage is labeled
            # Idempotent within the day.
            n2 = await _archive_weather_vintage(session)
            await session.commit()
            assert n2 == 0
        finally:
            await session.execute(
                delete(WeatherForecastVintage).where(
                    WeatherForecastVintage.vintage_date == today
                )
            )
            await session.commit()
