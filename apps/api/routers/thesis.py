"""Routes for the Working Thesis card (Phase 12).

Endpoints:
- GET    /v1/thesis/current        — return the active thesis for an instrument or 404
- GET    /v1/thesis/seed           — synthesize a draft from latest forecast + scenario
- POST   /v1/thesis                — create, deactivating the previous active one
- PATCH  /v1/thesis/{id}           — partial update of an existing thesis
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.models.orm.theses import Thesis
from apps.api.repos import forecasts as forecasts_repo
from apps.api.repos import instruments as instruments_repo
from apps.api.repos import scenarios as scenarios_repo
from apps.api.repos import theses as theses_repo
from apps.api.services.llm_explainer import critique_thesis as llm_critique_thesis

router = APIRouter(prefix="/v1/thesis", tags=["thesis"])


# ── Pydantic schemas ──────────────────────────────────────────────────────


class EvidenceEntry(BaseModel):
    factor: str = Field(min_length=1, max_length=200)
    weight: float | None = Field(default=None, ge=-1.0, le=1.0)
    note: str = Field(default="", max_length=500)
    source: str | None = Field(default=None, max_length=120)


class ThesisCreateRequest(BaseModel):
    instrument_code: str = Field(default="NG", max_length=20)
    statement: str = Field(min_length=1, max_length=2000)
    supporting_evidence: list[EvidenceEntry] = Field(default_factory=list, max_length=20)
    contradicting_evidence: list[EvidenceEntry] = Field(default_factory=list, max_length=20)
    missing_data: list[str] = Field(default_factory=list, max_length=20)
    conviction_pct: int = Field(ge=0, le=100)


class ThesisPatchRequest(BaseModel):
    statement: str | None = Field(default=None, min_length=1, max_length=2000)
    supporting_evidence: list[EvidenceEntry] | None = Field(default=None, max_length=20)
    contradicting_evidence: list[EvidenceEntry] | None = Field(default=None, max_length=20)
    missing_data: list[str] | None = Field(default=None, max_length=20)
    conviction_pct: int | None = Field(default=None, ge=0, le=100)


# ── Routes ────────────────────────────────────────────────────────────────


@router.get("/current")
async def get_current(
    instrument_code: str = "NG",
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    thesis = await theses_repo.get_active(session, instrument_code=instrument_code)
    if thesis is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active thesis for instrument {instrument_code!r}",
        )
    return _serialize(thesis)


@router.get("/seed")
async def get_seed_draft(
    instrument_code: str = "NG",
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Draft a fresh thesis from the latest forecast and scenario run.

    Not persisted — the caller submits a POST /v1/thesis once edited. If no
    forecasts or scenarios exist, returns a minimal scaffold so the form is
    still usable.
    """
    instrument = await instruments_repo.get_by_symbol(session, instrument_code)
    supporting: list[dict[str, Any]] = []
    contradicting: list[dict[str, Any]] = []

    if instrument is not None:
        # Pull forecasts from the last 7 days (one per model is typical).
        to_dt = datetime.utcnow()
        from_dt = to_dt - timedelta(days=7)
        recent = await forecasts_repo.get_history(
            session,
            instrument_id=instrument.id,
            from_dt=from_dt,
            to_dt=to_dt,
            limit=50,
        )
        for f in recent:
            for entry in (f.supporting or [])[:3]:
                supporting.append(_evidence_with_source(entry, f.model_name))
            for entry in (f.contradicting or [])[:3]:
                contradicting.append(_evidence_with_source(entry, f.model_name))

    supporting = _top_by_weight(supporting, limit=5)
    contradicting = _top_by_weight(contradicting, limit=5)

    # Missing data — start with the latest scenario run's data_needed_to_validate,
    # then top up with the fixed cadence list so the user always sees something.
    missing: list[str] = []
    recent_scenarios = await scenarios_repo.get_recent(session, limit=5)
    for s in recent_scenarios:
        result = s.result or {}
        for item in (result.get("data_needed_to_validate") or []):
            if item not in missing:
                missing.append(item)
        if len(missing) >= 5:
            break
    for item in _DEFAULT_MISSING_DATA:
        if item not in missing:
            missing.append(item)
    missing = missing[:8]

    return {
        "instrument_code": instrument_code,
        "statement": "",
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,
        "missing_data": missing,
        "conviction_pct": 50,
    }


@router.post("")
async def create_thesis(
    req: ThesisCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        fresh = await theses_repo.replace_active(
            session,
            instrument_code=req.instrument_code,
            statement=req.statement,
            supporting_evidence=[e.model_dump() for e in req.supporting_evidence],
            contradicting_evidence=[e.model_dump() for e in req.contradicting_evidence],
            missing_data=req.missing_data,
            conviction_pct=req.conviction_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _serialize(fresh)


@router.post("/{thesis_id}/critique")
async def critique_thesis(
    thesis_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run an LLM critique on the named thesis. Returns structured pushback
    plus a safety envelope. The thesis itself is not modified."""
    thesis = await theses_repo.get_by_id(session, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")

    payload = {
        "statement": thesis.statement,
        "supporting_evidence": thesis.supporting_evidence,
        "contradicting_evidence": thesis.contradicting_evidence,
        "missing_data": thesis.missing_data,
        "conviction_pct": thesis.conviction_pct,
    }
    critique, safety = await llm_critique_thesis(payload)
    return {
        "missed_risks": critique["missed_risks"],
        "blind_spots": critique["blind_spots"],
        "questions": critique["questions"],
        "safety": safety.model_dump(mode="json"),
    }


@router.patch("/{thesis_id}")
async def patch_thesis(
    thesis_id: uuid.UUID,
    req: ThesisPatchRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    thesis = await theses_repo.get_by_id(session, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")
    if not thesis.active:
        raise HTTPException(
            status_code=409, detail="Cannot edit a deactivated thesis"
        )

    patch_data: dict[str, Any] = {}
    if req.statement is not None:
        patch_data["statement"] = req.statement
    if req.supporting_evidence is not None:
        patch_data["supporting_evidence"] = [e.model_dump() for e in req.supporting_evidence]
    if req.contradicting_evidence is not None:
        patch_data["contradicting_evidence"] = [e.model_dump() for e in req.contradicting_evidence]
    if req.missing_data is not None:
        patch_data["missing_data"] = req.missing_data
    if req.conviction_pct is not None:
        patch_data["conviction_pct"] = req.conviction_pct

    try:
        updated = await theses_repo.patch_active(session, thesis, patch_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _serialize(updated)


# ── Helpers ───────────────────────────────────────────────────────────────


_DEFAULT_MISSING_DATA: list[str] = [
    "EIA Weekly Storage Report (Thu 10:30 ET)",
    "NWS 6-10 day temperature anomaly map",
    "CFTC Commitments of Traders (Fri 15:30 ET)",
]


def _evidence_with_source(entry: dict[str, Any], model_name: str) -> dict[str, Any]:
    """Normalize a forecast's supporting/contradicting dict into our shape."""
    return {
        "factor": str(entry.get("factor", "")),
        "weight": entry.get("weight"),
        "note": str(entry.get("note", "")),
        "source": model_name,
    }


def _top_by_weight(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Dedupe by factor and keep the top-N by absolute weight."""
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["factor"].lower()
        if key not in seen:
            seen[key] = item
            continue
        # Keep the entry with the larger absolute weight.
        existing_w = abs(seen[key].get("weight") or 0)
        new_w = abs(item.get("weight") or 0)
        if new_w > existing_w:
            seen[key] = item
    ranked = sorted(
        seen.values(), key=lambda e: abs(e.get("weight") or 0), reverse=True
    )
    return ranked[:limit]


def _serialize(thesis: Thesis) -> dict[str, Any]:
    return {
        "id": str(thesis.id),
        "instrument_code": thesis.instrument_code,
        "statement": thesis.statement,
        "supporting_evidence": thesis.supporting_evidence,
        "contradicting_evidence": thesis.contradicting_evidence,
        "missing_data": thesis.missing_data,
        "conviction_pct": thesis.conviction_pct,
        "created_at": thesis.created_at.isoformat(),
        "updated_at": thesis.updated_at.isoformat(),
        "active": thesis.active,
    }
