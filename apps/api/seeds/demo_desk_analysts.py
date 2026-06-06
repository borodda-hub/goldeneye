"""Seed demo analysts for the Desk Calibration Score (Phase 7).

Three synthetic analysts with distinct calibration profiles so the desk
leaderboard tells the skill-vs-luck story out of the box:
- well-calibrated  (conviction tracks outcomes)
- overconfident    (high conviction, mediocre outcomes)
- underconfident   (low conviction, strong outcomes)

Idempotent: deletes these demo user_ids' entries, then re-inserts. Run with:
    python -m apps.api.seeds.demo_desk_analysts
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Deterministic ids so re-runs replace rather than duplicate.
_NS = uuid.UUID("d0d0d0d0-0000-4000-8000-000000000000")
# (label, conviction, hits, misses)
_ANALYSTS = [
    ("well-calibrated", 65, 9, 5),
    ("overconfident", 85, 6, 8),
    ("underconfident", 55, 10, 4),
]


async def go() -> None:
    import apps.api.models.orm.instruments  # noqa: F401
    import apps.api.models.orm.theses  # noqa: F401  (FK target)
    import apps.api.models.orm.journal  # noqa: F401
    from sqlalchemy import delete, select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.instruments import Instrument
    from apps.api.models.orm.journal import UserDecisionJournal

    user_ids = [uuid.uuid5(_NS, label) for label, *_ in _ANALYSTS]
    base = datetime(2026, 4, 1, 12, 0, 0)

    async with get_session_factory()() as s:
        ng = (
            await s.execute(select(Instrument).where(Instrument.symbol == "NG"))
        ).scalar_one_or_none()
        if ng is None:
            print("error: NG instrument not seeded — run load_fixtures first")
            return

        await s.execute(
            delete(UserDecisionJournal).where(
                UserDecisionJournal.user_id.in_(user_ids)
            )
        )

        total = 0
        for (label, conviction, hits, misses), uid in zip(_ANALYSTS, user_ids):
            outcomes = ["hit"] * hits + ["miss"] * misses
            for i, outcome in enumerate(outcomes):
                s.add(
                    UserDecisionJournal(
                        id=uuid.uuid4(),
                        created_at=base + timedelta(days=i),
                        user_id=uid,
                        instrument_id=ng.id,
                        hypothesis=f"[demo:{label}] NG directional call #{i + 1}",
                        evidence=[],
                        confidence_pct=conviction,
                        thesis_conviction_at_write=conviction,
                        resolved_direction=outcome,
                        auto_resolved=True,
                    )
                )
                total += 1
            print(f"  {label}: {hits}/{hits + misses} hits @ {conviction}% conviction")
        await s.commit()
        print(f"\nSeeded {total} resolved demo decisions across {len(_ANALYSTS)} analysts.")


if __name__ == "__main__":
    asyncio.run(go())
