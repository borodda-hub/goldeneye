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


async def refresh_tick() -> dict[str, int]:
    """One refresh cycle: fetch latest reports → upsert → re-observe
    provenance. Returns per-source affected-row counts for logging/tests."""
    from apps.api.adapters.energy.eia import EIAAdapter
    from apps.api.adapters.positioning.cftc import MARKETS, CFTCAdapter
    from apps.api.db.session import get_session_factory
    from apps.api.repos import cot as cot_repo
    from apps.api.repos import eia as eia_repo
    from apps.api.services.feature_provenance import observe_feature_provenance

    counts = {"cot": 0, "storage": 0}
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
