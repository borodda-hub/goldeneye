"""Observed (not configured) provenance of the alt-data feature tables (31d).

Issue #13's core lesson: *configured* and *observed* diverge — prod was
configured for real EIA yet served stale mock. The LLM caveat's
positioning/storage clause therefore must derive from what the database
actually holds, not from adapter env vars.

A row counts as "real" only if its source is the real adapter's AND it is
fresh (published within `_FRESH_DAYS`) — real-but-frozen data (a dead
ingestion job) must not be advertised as real.

The observation is cached process-wide so the synchronous
`data_provenance_caveat()` can read it with zero call-site changes. It is
refreshed by (a) a one-shot observation at app boot and (b) every feature-
refresh scheduler tick (`services/feature_refresh.py`). When no observation
has run (tests, cold starts), the caveat falls back to its conservative
"illustrative" wording — never overclaiming.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Both feeds are weekly; 21 days tolerates release lags + holiday schedule
# shifts while still catching a dead ingestion job within ~2 missed cycles.
_FRESH_DAYS = 21

_COT_REAL_SOURCE = "cftc"
_STORAGE_REAL_SOURCE = "eia"


@dataclass(frozen=True)
class FeatureProvenance:
    cot_real: bool
    storage_real: bool
    observed_at: datetime


_cached: FeatureProvenance | None = None


def cached_feature_provenance() -> FeatureProvenance | None:
    return _cached


def set_cached_feature_provenance(value: FeatureProvenance | None) -> None:
    """Test seam + cache writer. Production writes go through
    `observe_feature_provenance`."""
    global _cached
    _cached = value


def _fresh(d: date | None, today: date) -> bool:
    return d is not None and 0 <= (today - d).days <= _FRESH_DAYS


def derive_feature_provenance(
    cot_source: str | None,
    cot_release_date: date | None,
    storage_source: str | None,
    storage_report_date: date | None,
    today: date,
) -> tuple[bool, bool]:
    """Pure derivation: (cot_real, storage_real). Real = real-adapter source
    AND fresh — stale-real reads as not-real (honest degradation)."""
    cot_real = cot_source == _COT_REAL_SOURCE and _fresh(cot_release_date, today)
    storage_real = storage_source == _STORAGE_REAL_SOURCE and _fresh(
        storage_report_date, today
    )
    return cot_real, storage_real


async def observe_feature_provenance(session: AsyncSession) -> FeatureProvenance:
    """Read the latest COT/storage rows and refresh the process-wide cache."""
    from apps.api.repos import cot as cot_repo
    from apps.api.repos import eia as eia_repo

    latest_cot = await cot_repo.get_latest(session)
    latest_storage = await eia_repo.get_latest(session)
    now = datetime.now(UTC)
    cot_real, storage_real = derive_feature_provenance(
        latest_cot.source if latest_cot else None,
        latest_cot.release_date if latest_cot else None,
        latest_storage.source if latest_storage else None,
        latest_storage.report_date if latest_storage else None,
        now.date(),
    )
    prov = FeatureProvenance(
        cot_real=cot_real, storage_real=storage_real, observed_at=now
    )
    set_cached_feature_provenance(prov)
    logger.info(
        "feature provenance observed: cot_real=%s storage_real=%s",
        cot_real,
        storage_real,
    )
    return prov


async def observe_once_on_boot() -> None:
    """One-shot boot observation (always runs, even with the refresh scheduler
    disabled) so a manually-backfilled DB gets an accurate caveat. Failures
    leave the conservative fallback in place — never crash the app."""
    try:
        from apps.api.db.session import get_session_factory

        async with get_session_factory()() as session:
            await observe_feature_provenance(session)
    except Exception:  # noqa: BLE001 — boot must not die over a label
        logger.exception("boot feature-provenance observation failed; caveat "
                         "stays conservative")
