"""Signal Quality grade endpoint (Phase 13 step 2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import price_bars as price_repo
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.signal_quality import compute_grade

router = APIRouter(prefix="/v1/signal-quality", tags=["signal-quality"])


@router.get("")
async def get_signal_quality(
    symbol: str = Query(default="NG"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=100,
    )

    ctx = ForecastContext(symbol=symbol, closes=closes)
    results = await run_all(ctx)
    ensemble = compute_ensemble(results)

    grade = await compute_grade(session, instrument_id=instrument.id, ensemble=ensemble)
    return {
        "symbol": symbol,
        "grade": grade.grade,
        "total_score": grade.total_score,
        "sub_scores": grade.sub_scores,
        "sub_score_max": grade.sub_score_max,
        "detail": grade.detail,
    }
