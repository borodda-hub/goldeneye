"""Positioning endpoint (Phase 18) — latest CFTC managed-money net per instrument."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.services.positioning import get_positioning

router = APIRouter(prefix="/v1/positioning", tags=["positioning"])


@router.get("")
async def get_positioning_endpoint(
    symbol: str = Query(default="NG"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")
    return await get_positioning(session, instrument)
