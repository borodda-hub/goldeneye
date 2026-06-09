"""Auto-resolution scheduler (Phase B1).

Runs the existing, look-ahead-safe `resolve_open_decisions` on a cadence so the
calibration ledger compounds without a manual endpoint call. This is a
**privileged system job**: it runs outside any user request, with a system
session, and resolves *every* open decision (no per-user scope — see
`docs/PHASE_B1_PLAN.md §2`). It never crosses users: it reads/writes only each
decision's own fields, so B3's per-user isolation is preserved (each analyst
still sees only their own resolved ledger).

Idempotent by construction: `resolve_open_decisions` only touches rows with
`resolved_direction IS NULL`, so re-running never double-resolves or overwrites.

Mechanism mirrors `realtime/ticker.py::start_ticker` — an in-process asyncio loop
launched from the app lifespan, **only when `settings.auto_resolve_enabled`**
(default OFF). The timing loop is thin glue; the load-bearing unit is
`resolve_tick`, which is locked in the gated `tests/db` suite.
"""

from __future__ import annotations

import asyncio
import logging

from apps.api.services.auto_resolution import ResolveResult, resolve_open_decisions

logger = logging.getLogger(__name__)


async def resolve_tick() -> ResolveResult:
    """One resolution cycle: a fresh system session → resolve → commit.

    Uses ``get_session_factory`` (never a request-scoped ``get_db``) because this
    runs outside any HTTP request. Returns the ``ResolveResult`` for logging/tests.
    """
    from apps.api.db.session import get_session_factory

    async with get_session_factory()() as session:
        result = await resolve_open_decisions(session)
        await session.commit()
    return result


async def run_scheduler(interval_seconds: float) -> None:
    """Resolve once on boot, then every ``interval_seconds``. Survives transient
    errors (logs + continues) so one bad cycle never kills the loop."""
    while True:
        try:
            result = await resolve_tick()
            if result.resolved:
                logger.info(
                    "auto-resolve: resolved %d decision(s) %s",
                    result.resolved,
                    dict(result.by_outcome),
                )
        except Exception:  # noqa: BLE001 — a background loop must not die
            logger.exception("auto-resolve tick failed; will retry next interval")
        await asyncio.sleep(interval_seconds)


def start_scheduler() -> None:
    """Launch the background loop when enabled. Called from the app lifespan."""
    from apps.api.src.settings import settings

    if not settings.auto_resolve_enabled:
        logger.info("auto-resolve scheduler disabled (auto_resolve_enabled=False)")
        return
    interval = max(60.0, settings.auto_resolve_interval_hours * 3600.0)
    asyncio.create_task(run_scheduler(interval))
    logger.info(
        "auto-resolve scheduler started (every %.1fh, boot tick first)",
        settings.auto_resolve_interval_hours,
    )
