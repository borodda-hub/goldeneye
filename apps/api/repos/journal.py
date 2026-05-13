from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal

# Permitted values for resolved_direction (kept here so route + repo agree).
RESOLVED_DIRECTIONS: frozenset[str] = frozenset(
    {"hit", "miss", "neutral", "unresolved"}
)


async def create(
    session: AsyncSession, instrument_id: uuid.UUID, data: dict[str, Any]
) -> UserDecisionJournal:
    entry = UserDecisionJournal(instrument_id=instrument_id, **data)
    session.add(entry)
    await session.flush()
    return entry


async def get_recent(session: AsyncSession, limit: int = 20) -> list[UserDecisionJournal]:
    result = await session.execute(
        select(UserDecisionJournal).order_by(UserDecisionJournal.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, entry_id: uuid.UUID) -> UserDecisionJournal | None:
    result = await session.execute(
        select(UserDecisionJournal).where(UserDecisionJournal.id == entry_id)
    )
    return result.scalar_one_or_none()


async def update(
    session: AsyncSession, entry: UserDecisionJournal, patch: dict[str, Any]
) -> UserDecisionJournal:
    """Apply a partial update to a journal entry.

    Permitted patch fields: outcome, reflection, llm_review, resolved_direction.
    Unknown keys are silently dropped — callers should validate via Pydantic.
    resolved_direction is validated against the RESOLVED_DIRECTIONS set;
    invalid values raise ValueError before any column mutation.
    """
    allowed = {
        "outcome",
        "reflection",
        "llm_review",
        "resolved_direction",
    }
    for key, val in patch.items():
        if key not in allowed:
            continue
        if key == "resolved_direction":
            if val is not None and val not in RESOLVED_DIRECTIONS:
                raise ValueError(
                    f"resolved_direction must be one of {sorted(RESOLVED_DIRECTIONS)} or null, "
                    f"got {val!r}"
                )
        setattr(entry, key, val)
    await session.flush()
    return entry


async def list_with_resolutions(
    session: AsyncSession, instrument_id: uuid.UUID
) -> list[UserDecisionJournal]:
    """All journal entries for an instrument — regardless of resolution state.

    The calibration service consumes this and computes its own filtering. We
    return everything (resolved + unresolved + null) so the page can show both
    "n=14 entries scored" and "n=3 unresolved" counts.
    """
    result = await session.execute(
        select(UserDecisionJournal)
        .where(UserDecisionJournal.instrument_id == instrument_id)
        .order_by(UserDecisionJournal.created_at.desc())
    )
    return list(result.scalars().all())
