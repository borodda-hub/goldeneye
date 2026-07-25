"""Live COT/EIA feature refresh scheduler (Phase 31d).

Keeps `cot_reports` / `eia_storage_reports` current in a deployment by
periodically fetching the latest weekly reports through the REAL adapters and
upserting via the 31a repos (the tables' UNIQUE keys make every tick
idempotent). Each tick ends by re-observing feature provenance so the LLM
caveat (`services/feature_provenance.py`) tracks reality.

Mirrors the B1 auto-resolution scheduler: an in-process asyncio loop launched
from the app lifespan, **only when `settings.feature_refresh_enabled`**
(default OFF — dev/demo stays mock unless the deep backfill has been run).
This is the convenience tier, not the heavy ingestion worker; the deep
historical load is `seeds/backfill_features.py` (manual, deliberate).

The EIA leg silently no-ops without `EIA_API_KEY` (the adapter returns []).
Per-source failures log and continue — one bad feed never kills the loop or
the other feed's refresh.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Latest-N weekly reports per tick — plenty to catch up after downtime while
# staying a trivial fetch (the deep backfill owns history).
_RECENT_REPORTS = 8


def _jsonable(value):  # type: ignore[no-untyped-def]
    """Recursively convert dates/datetimes to ISO strings so the adapter's
    forecast dicts (which carry `ts` objects) survive the JSONB boundary
    verbatim-in-shape."""
    import datetime as _dt

    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


async def _archive_weather_vintage(session) -> int:  # type: ignore[no-untyped-def]
    """Phase D5: persist today's forecast vintage (6 regions + the US
    aggregate anomaly) from whatever weather adapter is configured. The
    UNIQUE (vintage_date, region) key + insert-only repo make same-day
    re-ticks no-ops — a past vintage is never rewritten. `source` labels
    mock vintages so a future validation can exclude them."""
    from datetime import date as _date

    from apps.api.adapters.registry import get_weather
    from apps.api.adapters.weather.regions import REGION_POINTS
    from apps.api.repos import weather_vintages as wv_repo
    from apps.api.src.settings import settings

    today = _date.today()
    weather = get_weather()
    source = settings.adapter_weather or "mock"
    rows: list[dict] = []
    for region in REGION_POINTS:
        forecast = await weather.get_forecast(region)
        if forecast:
            rows.append(
                {
                    "vintage_date": today,
                    "region": region,
                    "forecast": _jsonable(forecast),
                    "national_hdd_anomaly": None,
                    "source": source,
                }
            )
    anomaly = await weather.get_national_hdd_anomaly()
    rows.append(
        {
            "vintage_date": today,
            "region": "US",
            "forecast": [],
            "national_hdd_anomaly": float(anomaly),
            "source": source,
        }
    )
    return await wv_repo.insert_vintages(session, rows)


async def _archive_curve_vintage(session) -> int:  # type: ignore[no-untyped-def]
    """Phase D2a: persist today's futures-curve snapshot per symbol. Yahoo
    drops expired contract months, so the historical curve is otherwise
    unreconstructible — this archive is the only path to full-fidelity
    carry validation later. Same immutability doctrine as the weather
    archive (insert-only; same-day re-ticks are no-ops)."""
    from datetime import UTC as _UTC
    from datetime import date as _date
    from datetime import datetime as _datetime

    from apps.api.adapters.registry import get_market
    from apps.api.repos import curve_vintages as cv_repo
    from apps.api.src.settings import settings

    today = _date.today()
    market = get_market()
    source = settings.adapter_market or "mock"
    now = _datetime.now(_UTC).replace(tzinfo=None)
    rows: list[dict] = []
    for symbol in _CURVE_SYMBOLS:
        try:
            curve = await market.get_curve_snapshot(symbol, now)
        except Exception:  # noqa: BLE001 — one symbol must not kill the leg
            logger.exception("curve snapshot failed for %s", symbol)
            continue
        if curve:
            rows.append(
                {
                    "vintage_date": today,
                    "symbol": symbol,
                    "curve": _jsonable(curve),
                    "source": source,
                }
            )
    return await cv_repo.insert_vintages(session, rows)


# Futures curves worth archiving — the six commodities (ES/ZN curves are not
# served per-month by the current adapter path).
_CURVE_SYMBOLS = ("NG", "CL", "HO", "RB", "GC", "SI")


async def refresh_tick() -> dict[str, int]:
    """One refresh cycle: fetch latest reports → upsert → archive today's
    weather + curve vintages → re-observe provenance. Returns per-source
    affected-row counts for logging/tests."""
    from apps.api.adapters.energy.eia import EIAAdapter
    from apps.api.adapters.positioning.cftc import MARKETS, CFTCAdapter
    from apps.api.db.session import get_session_factory
    from apps.api.repos import cot as cot_repo
    from apps.api.repos import eia as eia_repo
    from apps.api.services.feature_provenance import observe_feature_provenance

    counts = {"cot": 0, "storage": 0, "weather": 0, "curve": 0}
    async with get_session_factory()() as session:
        for symbol in MARKETS:
            try:
                rows = await CFTCAdapter(symbol).get_cot_reports(
                    limit=_RECENT_REPORTS
                )
                counts["cot"] += await cot_repo.upsert_many(session, rows)
            except Exception:  # noqa: BLE001 — one market must not kill the tick
                logger.exception("COT refresh failed for %s", symbol)
        try:
            rows = await EIAAdapter().get_storage_reports(limit=_RECENT_REPORTS)
            counts["storage"] += await eia_repo.upsert_many(session, rows)
        except Exception:  # noqa: BLE001
            logger.exception("EIA storage refresh failed")
        try:
            counts["weather"] = await _archive_weather_vintage(session)
        except Exception:  # noqa: BLE001 — D5 archival must not kill the tick
            logger.exception("weather vintage archival failed")
        try:
            counts["curve"] = await _archive_curve_vintage(session)
        except Exception:  # noqa: BLE001 — D2a archival must not kill the tick
            logger.exception("curve vintage archival failed")
        await session.commit()
        await observe_feature_provenance(session)
    return counts


async def run_feature_refresh(interval_seconds: float) -> None:
    """Refresh once on boot, then every ``interval_seconds``. Survives errors."""
    while True:
        try:
            counts = await refresh_tick()
            logger.info("feature refresh: %s rows upserted", counts)
        except Exception:  # noqa: BLE001 — a background loop must not die
            logger.exception("feature refresh tick failed; will retry")
        await asyncio.sleep(interval_seconds)


def start_feature_refresh() -> None:
    """Launch the loop when enabled. Called from the app lifespan."""
    from apps.api.src.settings import settings

    if not settings.feature_refresh_enabled:
        logger.info(
            "feature refresh disabled (feature_refresh_enabled=False)"
        )
        return
    interval = max(60.0, settings.feature_refresh_interval_hours * 3600.0)
    asyncio.create_task(run_feature_refresh(interval))
    logger.info(
        "feature refresh started (every %.1fh, boot tick first)",
        settings.feature_refresh_interval_hours,
    )
