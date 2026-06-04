"""Pattern endpoints (Phase 21 + 24) over a contract's bars.

GET /v1/chart/patterns — candlestick-pattern detections (Phase 21).
GET /v1/chart/auto-ta   — auto support/resistance, trendlines, and chart
                          patterns (Phase 24).

Both are *descriptive observations*, not trade signals: responses carry the
safety envelope and the strings are written in the cautious desk-analyst voice.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.registry import get_market
from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.services.patterns import detect_auto_ta, detect_patterns
from apps.api.services.safety import wrap_with_uncertainty

router = APIRouter(prefix="/v1/chart", tags=["chart"])

_CANDLE_CAVEATS = [
    "Candlestick patterns describe recent price action; they are not predictions.",
    "A pattern reads more reliably with volume and trend confirmation.",
]
_AUTOTA_CAVEATS = [
    "Support/resistance, trendlines, and chart patterns are descriptive — not predictions.",
    "Levels and patterns confirm only on a decisive break, ideally with volume.",
]


async def _fetch_bars(
    session: AsyncSession,
    contract_code: str,
    resolution: str,
    from_: date,
    to: date,
) -> tuple[list[dict[str, Any]], datetime]:
    contract = await contract_repo.get_by_code(session, contract_code)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Contract {contract_code!r} not found"
        )
    market = get_market()
    from_dt = datetime(from_.year, from_.month, from_.day)
    to_dt = datetime(to.year, to.month, to.day, 23, 59, 59)
    bars = await market.get_bars(contract_code, resolution, from_dt=from_dt, to_dt=to_dt)
    as_of = bars[-1]["ts"] if bars else to_dt
    as_of_dt = as_of if isinstance(as_of, datetime) else to_dt
    return bars, as_of_dt


@router.get("/patterns")
async def get_patterns(
    contract_code: str = Query(...),
    resolution: str = Query(default="1d"),
    from_: date = Query(default=date(2025, 5, 10), alias="from"),
    to: date = Query(default_factory=date.today),
    limit: int = Query(default=120, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> dict:
    bars, as_of_dt = await _fetch_bars(session, contract_code, resolution, from_, to)
    detections = detect_patterns(bars)[-limit:]
    safety = wrap_with_uncertainty(
        detections, confidence="low", caveats=_CANDLE_CAVEATS, as_of=as_of_dt
    )
    return {
        "contract_code": contract_code,
        "resolution": resolution,
        "patterns": detections,
        "safety": safety.model_dump(mode="json"),
    }


@router.get("/auto-ta")
async def get_auto_ta(
    contract_code: str = Query(...),
    resolution: str = Query(default="1d"),
    from_: date = Query(default=date(2025, 5, 10), alias="from"),
    to: date = Query(default_factory=date.today),
    session: AsyncSession = Depends(get_db),
) -> dict:
    bars, as_of_dt = await _fetch_bars(session, contract_code, resolution, from_, to)
    result = detect_auto_ta(bars)
    safety = wrap_with_uncertainty(
        result, confidence="low", caveats=_AUTOTA_CAVEATS, as_of=as_of_dt
    )
    return {
        "contract_code": contract_code,
        "resolution": resolution,
        **result,
        "safety": safety.model_dump(mode="json"),
    }
