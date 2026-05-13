from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import journal as journal_repo
from apps.api.repos import theses as theses_repo
from apps.api.services.llm_explainer import review_journal_entry

router = APIRouter(prefix="/v1/journal", tags=["journal"])


class EvidenceItem(BaseModel):
    source: str
    summary: str
    weight: float = 0.5


class JournalCreateRequest(BaseModel):
    instrument: str = "NG"
    hypothesis: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence_pct: int = Field(ge=0, le=100)
    planned_action: str | None = None
    risk_factors: list[str] = Field(default_factory=list)
    invalidation_criteria: str | None = None


class JournalPatchRequest(BaseModel):
    outcome: str | None = None
    reflection: str | None = None
    resolved_direction: Literal["hit", "miss", "neutral", "unresolved"] | None = None


@router.post("")
async def create_entry(
    req: JournalCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, req.instrument)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.instrument!r} not found")

    # Phase 13: snapshot the active thesis at write time so calibration can
    # attribute outcomes back to the conviction-at-decision. Both columns
    # stay NULL when no active thesis exists for the instrument; the entry
    # falls back to its own confidence_pct in calibration.
    active_thesis = await theses_repo.get_active(
        session, instrument_code=req.instrument
    )

    data: dict[str, Any] = {
        "hypothesis": req.hypothesis,
        "evidence": [e.model_dump() for e in req.evidence],
        "confidence_pct": req.confidence_pct,
        "planned_action": req.planned_action,
        "risk_factors": req.risk_factors or None,
        "invalidation_criteria": req.invalidation_criteria,
    }
    if active_thesis is not None:
        data["thesis_id_at_write"] = active_thesis.id
        data["thesis_conviction_at_write"] = active_thesis.conviction_pct

    entry = await journal_repo.create(session, instrument.id, data)

    # Trigger async LLM review
    entry_dict = {
        "hypothesis": req.hypothesis,
        "evidence": [e.model_dump() for e in req.evidence],
        "confidence_pct": req.confidence_pct,
        "planned_action": req.planned_action,
        "risk_factors": req.risk_factors,
        "invalidation_criteria": req.invalidation_criteria,
    }
    try:
        review_text, safety_env = await review_journal_entry(entry_dict)
        # mode="json" so the datetime in as_of becomes an ISO string —
        # llm_review is persisted to the user_decision_journals.llm_review
        # JSONB column.
        llm_review = {"text": review_text, "safety": safety_env.model_dump(mode="json")}
        entry = await journal_repo.update(session, entry, {"llm_review": llm_review})
    except Exception:
        pass  # review is best-effort

    await session.commit()
    return _serialize(entry)


@router.get("")
async def list_entries(
    limit: int = 20,
    symbol: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List recent entries. When ?symbol= is supplied, filter to that
    instrument; otherwise return entries across all instruments (legacy
    behavior preserved for callers that don't pass the param)."""
    instrument_id = None
    if symbol:
        instrument = await instr_repo.get_by_symbol(session, symbol)
        if instrument is None:
            raise HTTPException(
                status_code=404, detail=f"Instrument {symbol!r} not found"
            )
        instrument_id = instrument.id
    entries = await journal_repo.get_recent(
        session, limit=limit, instrument_id=instrument_id
    )
    return {"entries": [_serialize(e) for e in entries]}


@router.get("/{entry_id}")
async def get_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    entry = await journal_repo.get_by_id(session, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return _serialize(entry)


@router.patch("/{entry_id}")
async def patch_entry(
    entry_id: uuid.UUID,
    req: JournalPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    entry = await journal_repo.get_by_id(session, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    # Only include fields the client actually set — exclude_unset distinguishes
    # `{"resolved_direction": null}` (clear) from omitting the field entirely.
    patch = req.model_dump(exclude_unset=True)
    try:
        entry = await journal_repo.update(session, entry, patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _serialize(entry)


def _serialize(entry) -> dict:  # type: ignore[type-arg]
    return {
        "id": str(entry.id),
        "created_at": entry.created_at.isoformat(),
        "instrument_id": str(entry.instrument_id),
        "hypothesis": entry.hypothesis,
        "evidence": entry.evidence,
        "confidence_pct": entry.confidence_pct,
        "planned_action": entry.planned_action,
        "risk_factors": entry.risk_factors,
        "invalidation_criteria": entry.invalidation_criteria,
        "outcome": entry.outcome,
        "reflection": entry.reflection,
        "llm_review": entry.llm_review,
        "resolved_direction": entry.resolved_direction,
        "thesis_id_at_write": (
            str(entry.thesis_id_at_write) if entry.thesis_id_at_write else None
        ),
        "thesis_conviction_at_write": entry.thesis_conviction_at_write,
    }
