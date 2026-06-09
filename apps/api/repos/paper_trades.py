from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.paper import PaperTrade


async def create(session: AsyncSession, instrument_id: uuid.UUID, data: dict[str, Any]) -> PaperTrade:
    trade = PaperTrade(instrument_id=instrument_id, **data)
    session.add(trade)
    await session.flush()
    return trade


async def list_trades(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 50,
    instrument_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> list[PaperTrade]:
    """Trades for the requester scope. `user_id=None` = the shared anonymous pool
    (today's behavior); a real id = only that user's trades."""
    q = (
        select(PaperTrade)
        .where(PaperTrade.user_id == user_id)
        .order_by(PaperTrade.opened_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(PaperTrade.status == status)
    if instrument_id is not None:
        q = q.where(PaperTrade.instrument_id == instrument_id)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, trade_id: uuid.UUID) -> PaperTrade | None:
    result = await session.execute(select(PaperTrade).where(PaperTrade.id == trade_id))
    return result.scalar_one_or_none()


async def close_trade(
    session: AsyncSession,
    trade: PaperTrade,
    exit_price: float,
    reflection: str | None = None,
) -> PaperTrade:
    trade.exit_price = exit_price  # type: ignore[assignment]
    trade.closed_at = datetime.utcnow()
    trade.status = "closed"  # type: ignore[assignment]
    pnl = (exit_price - float(trade.entry_price)) * float(trade.size_contracts)
    if trade.side == "short":
        pnl = -pnl
    trade.outcome_pnl = pnl  # type: ignore[assignment]
    if reflection:
        trade.reflection = reflection  # type: ignore[assignment]
    await session.flush()
    return trade


async def list_open(session: AsyncSession) -> list[PaperTrade]:
    result = await session.execute(
        select(PaperTrade).where(PaperTrade.status == "open")
    )
    return list(result.scalars().all())


async def list_closed_between(
    session: AsyncSession,
    from_dt: datetime,
    to_dt: datetime,
) -> list[PaperTrade]:
    result = await session.execute(
        select(PaperTrade)
        .where(
            PaperTrade.status == "closed",
            PaperTrade.closed_at >= from_dt,
            PaperTrade.closed_at <= to_dt,
        )
    )
    return list(result.scalars().all())


async def list_opened_before(
    session: AsyncSession,
    cutoff: datetime,
) -> list[PaperTrade]:
    result = await session.execute(
        select(PaperTrade).where(PaperTrade.opened_at <= cutoff)
    )
    return list(result.scalars().all())
