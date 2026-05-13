"""Calibration endpoint (Phase 13 step 3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.services.calibration import (
    CalibrationBucket,
    CalibrationResult,
    compute_calibration,
)
from apps.api.services.dq_coach import coach_decision_quality

router = APIRouter(prefix="/v1/calibration", tags=["calibration"])


def _serialize_bucket(b: CalibrationBucket) -> dict:
    return {
        "label": b.label,
        "lower_pct": b.lower_pct,
        "upper_pct": b.upper_pct,
        "claimed_mean": b.claimed_mean,
        "total_count": b.total_count,
        "resolved_count": b.resolved_count,
        "hit_count": b.hit_count,
        "hit_rate": b.hit_rate,
    }


def _serialize(result: CalibrationResult) -> dict:
    return {
        "instrument_code": result.instrument_code,
        "buckets": [_serialize_bucket(b) for b in result.buckets],
        "total_entries": result.total_entries,
        "resolved_entries": result.resolved_entries,
        "unresolved_entries": result.unresolved_entries,
        "summary": result.summary,
    }


@router.get("")
async def get_calibration(
    instrument_code: str = Query(default="NG"),
    bucket_count: int = Query(default=5, ge=2, le=10),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, instrument_code)
    if instrument is None:
        raise HTTPException(
            status_code=404, detail=f"Instrument {instrument_code!r} not found"
        )

    try:
        result = await compute_calibration(
            session,
            instrument_id=instrument.id,
            instrument_code=instrument_code,
            bucket_count=bucket_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _serialize(result)


@router.get("/coaching")
async def get_coaching(
    instrument_code: str = Query(default="NG"),
    bucket_count: int = Query(default=5, ge=2, le=10),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """LLM-synthesized Decision Quality coaching per bucket + overall."""
    instrument = await instr_repo.get_by_symbol(session, instrument_code)
    if instrument is None:
        raise HTTPException(
            status_code=404, detail=f"Instrument {instrument_code!r} not found"
        )
    try:
        coaching, safety = await coach_decision_quality(
            session,
            instrument_id=instrument.id,
            instrument_code=instrument_code,
            bucket_count=bucket_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "instrument_code": instrument_code,
        "buckets": coaching["buckets"],
        "overall": coaching["overall"],
        "safety": safety.model_dump(mode="json"),
    }
