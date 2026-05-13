from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import paper_trades as trade_repo
from apps.api.services import paper_engine

router = APIRouter(prefix="/v1/paper-trades", tags=["paper-trades"])


class OpenTradeRequest(BaseModel):
    instrument: str = "NG"
    contract_code: str | None = None
    side: str  # long | short
    size_contracts: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    rationale: str | None = None
    journal_ref: uuid.UUID | None = None


class CloseTradeRequest(BaseModel):
    exit_price: float | None = None
    reflection: str | None = None


@router.post("/open")
async def open_trade(
    req: OpenTradeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, req.instrument)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.instrument!r} not found")

    contract_id: uuid.UUID | None = None
    if req.contract_code:
        contract = await contract_repo.get_by_code(session, req.contract_code)
        contract_id = contract.id if contract else None

    trade = await paper_engine.open_trade(
        session,
        instrument_id=instrument.id,
        contract_id=contract_id,
        side=req.side,
        size=req.size_contracts,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        rationale=req.rationale,
        journal_ref=req.journal_ref,
    )
    await session.commit()
    return _serialize(trade)


@router.post("/{trade_id}/close")
async def close_trade(
    trade_id: uuid.UUID,
    req: CloseTradeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    trade = await paper_engine.close_trade(
        session,
        trade_id,
        exit_price=req.exit_price,
        reflection=req.reflection,
    )
    await session.commit()
    return _serialize(trade)


@router.get("/equity-curve")
async def get_equity_curve(
    since: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    series = await paper_engine.equity_curve(session, since=since)
    return {"series": series}


@router.get("")
async def list_trades(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    symbol: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument_id = None
    if symbol:
        instrument = await instr_repo.get_by_symbol(session, symbol)
        if instrument is None:
            raise HTTPException(
                status_code=404, detail=f"Instrument {symbol!r} not found"
            )
        instrument_id = instrument.id
    trades = await trade_repo.list_trades(
        session, status=status, limit=limit, instrument_id=instrument_id
    )
    return {"trades": [_serialize(t) for t in trades]}


@router.get("/{trade_id}")
async def get_trade(
    trade_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    trade = await trade_repo.get_by_id(session, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return _serialize(trade)


def _serialize(trade) -> dict:  # type: ignore[type-arg]
    pnl: float | None = None
    if trade.status == "open" and trade.exit_price is None:
        pnl = None  # live PnL would be computed against current market price
    elif trade.outcome_pnl is not None:
        pnl = float(trade.outcome_pnl)

    return {
        "id": str(trade.id),
        "opened_at": trade.opened_at.isoformat(),
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
        "instrument_id": str(trade.instrument_id),
        "contract_id": str(trade.contract_id) if trade.contract_id else None,
        "side": trade.side,
        "size_contracts": float(trade.size_contracts),
        "entry_price": float(trade.entry_price),
        "exit_price": float(trade.exit_price) if trade.exit_price is not None else None,
        "stop_loss": float(trade.stop_loss) if trade.stop_loss is not None else None,
        "take_profit": float(trade.take_profit) if trade.take_profit is not None else None,
        "status": trade.status,
        "rationale": trade.rationale,
        "outcome_pnl": pnl,
        "reflection": trade.reflection,
        "journal_ref": str(trade.journal_ref) if trade.journal_ref else None,
    }
