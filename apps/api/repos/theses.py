"""Repository layer for theses (Phase 12 — Working Thesis card).

Conventions:
- "Active" = the currently displayed thesis for an instrument. Only one row per
  instrument has active=True; the unique partial index enforces this at the
  DB level.
- Creating a new thesis transparently deactivates the previous active one via
  `replace_active`. Callers should use that — not raw `create` + manual update.
- History is preserved: deactivated rows are kept for Phase 13 calibration.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.theses import Thesis


async def get_active(
    session: AsyncSession,
    instrument_code: str = "NG",
    user_id: uuid.UUID | None = None,
) -> Thesis | None:
    """Return the active thesis for an instrument within the requester scope, or
    None. `user_id=None` reads the shared anonymous pool (today's behavior); a real
    id reads only that user's active thesis (B3b passes it)."""
    result = await session.execute(
        select(Thesis)
        .where(
            Thesis.instrument_code == instrument_code,
            Thesis.active.is_(True),
            Thesis.user_id == user_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, thesis_id: uuid.UUID) -> Thesis | None:
    """Return any thesis by ID (active or historical)."""
    result = await session.execute(select(Thesis).where(Thesis.id == thesis_id))
    return result.scalar_one_or_none()


async def replace_active(
    session: AsyncSession,
    *,
    instrument_code: str,
    statement: str,
    supporting_evidence: list[dict[str, Any]],
    contradicting_evidence: list[dict[str, Any]],
    missing_data: list[str],
    conviction_pct: int,
    user_id: uuid.UUID | None = None,
) -> Thesis:
    """Deactivate the requester's current active thesis (if any) and insert a new one.

    Both operations happen in the same session/transaction; the caller is
    responsible for the surrounding commit. Raises ValueError on invalid
    `conviction_pct` to fail fast before hitting the CHECK constraint.

    **The deactivate is scoped to `user_id`** (incl. the `user_id IS NULL` anonymous
    pool). Without that scope, creating a thesis would deactivate *every other user's*
    active thesis for the same instrument — the B3 data-isolation landmine. The new
    row is stamped with the same `user_id`.
    """
    if not 0 <= conviction_pct <= 100:
        raise ValueError(
            f"conviction_pct must be 0-100, got {conviction_pct}"
        )
    if not statement.strip():
        raise ValueError("statement must be non-empty")

    await session.execute(
        sa_update(Thesis)
        .where(
            Thesis.instrument_code == instrument_code,
            Thesis.active.is_(True),
            Thesis.user_id == user_id,
        )
        .values(active=False)
    )
    fresh = Thesis(
        instrument_code=instrument_code,
        statement=statement.strip(),
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        missing_data=missing_data,
        conviction_pct=conviction_pct,
        active=True,
        user_id=user_id,
    )
    session.add(fresh)
    await session.flush()
    return fresh


async def patch_active(
    session: AsyncSession,
    thesis: Thesis,
    patch: dict[str, Any],
) -> Thesis:
    """Update select fields on an existing thesis row.

    Permitted fields: statement, supporting_evidence, contradicting_evidence,
    missing_data, conviction_pct. Silently drops unknown keys; callers should
    validate at the Pydantic layer.
    """
    allowed = {
        "statement",
        "supporting_evidence",
        "contradicting_evidence",
        "missing_data",
        "conviction_pct",
    }
    for key, val in patch.items():
        if key not in allowed:
            continue
        if key == "conviction_pct" and not 0 <= val <= 100:
            raise ValueError(f"conviction_pct must be 0-100, got {val}")
        if key == "statement" and not str(val).strip():
            raise ValueError("statement must be non-empty")
        setattr(thesis, key, val)
    await session.flush()
    return thesis
