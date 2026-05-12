from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import journal as journal_repo
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


@router.post("")
async def create_entry(
    req: JournalCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, req.instrument)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.instrument!r} not found")

    data: dict[str, Any] = {
        "hypothesis": req.hypothesis,
        "evidence": [e.model_dump() for e in req.evidence],
        "confidence_pct": req.confidence_pct,
        "planned_action": req.planned_action,
        "risk_factors": req.risk_factors or None,
        "invalidation_criteria": req.invalidation_criteria,
    }

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
    session: AsyncSession = Depends(get_db),
) -> dict:
    entries = await journal_repo.get_recent(session, limit=limit)
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
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    entry = await journal_repo.update(session, entry, patch)
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
    }
