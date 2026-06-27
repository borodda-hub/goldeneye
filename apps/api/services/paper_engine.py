"""
Paper trading engine: validation, PnL math, mark-to-market close, and equity curve.

Pure-Python service module sitting between `routers/paper.py` and the repos.
The router stays thin; this module owns engine math and HTTP-shaped validation.

Constants (NG-only for the demo):
    NG_TICK_VALUE_USD   $10,000/contract per $1.00 price move (NG = 10,000 MMBtu).
    STARTING_EQUITY_USD $100,000 paper-equity starting balance.
    LEVERAGE_CAP        Soft leverage cap = 10× current equity.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.paper import PaperTrade
from apps.api.models.orm.prices import PriceBar
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import paper_trades as trade_repo

# B5: the per-$1-move USD value of a contract is the instrument's contract_size
# (NG 10000, ES 50, ZN 1000). NG_TICK_VALUE_USD == NG's contract_size, kept as the
# fallback so compute_pnl/validate_open stay byte-identical for NG + the mocked
# unit tests; instrument-aware paths resolve the real value via _resolve_tick_value.
NG_TICK_VALUE_USD: float = 10_000.0
STARTING_EQUITY_USD: float = 100_000.0
LEVERAGE_CAP: float = 10.0


async def _resolve_tick_value(
    session: AsyncSession, instrument_id: uuid.UUID
) -> float:
    """The instrument's contract_size (per-$1-move USD value). Falls back to
    NG_TICK_VALUE_USD when the instrument can't be resolved to a numeric size — so
    the mocked unit tests (AsyncMock session → non-numeric attr) keep the NG value."""
    instr = await instr_repo.get_by_id(session, instrument_id)
    cs = getattr(instr, "contract_size", None)
    if isinstance(cs, (int, float, Decimal)):
        return float(cs)
    return NG_TICK_VALUE_USD


# ---------------------------------------------------------------------------
# Pure math
# ---------------------------------------------------------------------------
def compute_pnl(
    side: str,
    size: float,
    entry: float,
    exit_: float,
    tick_value: float = NG_TICK_VALUE_USD,
) -> float:
    """USD PnL. Long: (exit - entry) × size × tick. Short: inverted. Pure."""
    pnl = (exit_ - entry) * size * tick_value
    return -pnl if side == "short" else pnl


# ---------------------------------------------------------------------------
# Equity helpers
# ---------------------------------------------------------------------------
async def current_equity(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> float:
    """STARTING_EQUITY_USD + sum(outcome_pnl) over the requester's closed trades.
    `user_id=None` = the shared anonymous pool (today's behavior)."""
    result = await session.execute(
        select(PaperTrade).where(
            PaperTrade.status == "closed",
            PaperTrade.user_id == user_id,
        )
    )
    closed = list(result.scalars().all())
    realized = sum(float(t.outcome_pnl or 0.0) for t in closed)
    return STARTING_EQUITY_USD + realized


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
async def validate_open(
    session: AsyncSession,
    side: str,
    size: float,
    entry_price: float,
    stop_loss: float | None,
    take_profit: float | None,
    tick_value: float = NG_TICK_VALUE_USD,
) -> None:
    """
    Raises HTTPException 400 on bad inputs, 409 on leverage breach.

    400 conditions:
      - size <= 0
      - entry_price <= 0
      - side not in {"long", "short"}
      - long with stop_loss >= entry_price (when present)
      - long with take_profit <= entry_price (when present)
      - short with stop_loss <= entry_price (when present)
      - short with take_profit >= entry_price (when present)

    409 conditions:
      - notional = size × entry × NG_TICK_VALUE_USD > LEVERAGE_CAP × current_equity
    """
    if side not in {"long", "short"}:
        raise HTTPException(status_code=400, detail=f"Invalid side: {side!r}")
    if size <= 0:
        raise HTTPException(status_code=400, detail="size_contracts must be > 0")
    if entry_price <= 0:
        raise HTTPException(status_code=400, detail="entry_price must be > 0")

    if side == "long":
        if stop_loss is not None and stop_loss >= entry_price:
            raise HTTPException(
                status_code=400,
                detail="long stop_loss must be below entry_price",
            )
        if take_profit is not None and take_profit <= entry_price:
            raise HTTPException(
                status_code=400,
                detail="long take_profit must be above entry_price",
            )
    else:  # short
        if stop_loss is not None and stop_loss <= entry_price:
            raise HTTPException(
                status_code=400,
                detail="short stop_loss must be above entry_price",
            )
        if take_profit is not None and take_profit >= entry_price:
            raise HTTPException(
                status_code=400,
                detail="short take_profit must be below entry_price",
            )

    notional = size * entry_price * tick_value
    equity = await current_equity(session)
    cap = LEVERAGE_CAP * equity
    if notional > cap:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Leverage breach: notional ${notional:,.0f} exceeds "
                f"{LEVERAGE_CAP:.0f}× current equity (${equity:,.0f}); "
                f"max allowed ${cap:,.0f}."
            ),
        )


# ---------------------------------------------------------------------------
# Open / close
# ---------------------------------------------------------------------------
async def open_trade(
    session: AsyncSession,
    *,
    instrument_id: uuid.UUID,
    contract_id: uuid.UUID | None,
    side: str,
    size: float,
    entry_price: float,
    stop_loss: float | None,
    take_profit: float | None,
    rationale: str | None,
    journal_ref: uuid.UUID | None,
    user_id: uuid.UUID | None = None,
) -> PaperTrade:
    """Validates and persists a paper trade. Caller is responsible for commit.
    Stamped with `user_id` (None = anonymous pool; B3b passes the requester's id)."""
    await validate_open(
        session,
        side=side,
        size=size,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        tick_value=await _resolve_tick_value(session, instrument_id),
    )

    data: dict[str, Any] = {
        "side": side,
        "size_contracts": size,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "rationale": rationale,
        "journal_ref": journal_ref,
        "contract_id": contract_id,
        "status": "open",
        "user_id": user_id,
    }
    return await trade_repo.create(session, instrument_id, data)


async def _latest_close_price(
    session: AsyncSession,
    trade: PaperTrade,
) -> float | None:
    """
    Return the latest 1d close for the trade's bound contract, or fall back to the
    instrument's front-month contract if no contract is bound.
    """
    contract_id = trade.contract_id
    if contract_id is None:
        front = await contract_repo.get_front_month(session, trade.instrument_id)
        if front is None:
            return None
        contract_id = front.id

    result = await session.execute(
        select(PriceBar)
        .where(PriceBar.contract_id == contract_id, PriceBar.resolution == "1d")
        .order_by(PriceBar.ts.desc())
        .limit(1)
    )
    bar = result.scalar_one_or_none()
    if bar is None:
        return None
    # Prefer the mid; fall back to close.
    if bar.high is not None and bar.low is not None:
        return (float(bar.high) + float(bar.low)) / 2.0
    return float(bar.close)


async def close_trade(
    session: AsyncSession,
    trade_id: uuid.UUID,
    exit_price: float | None = None,
    reflection: str | None = None,
) -> PaperTrade:
    """
    Close a trade. If `exit_price` is None, mark-to-market off the latest 1d bar mid.
    409 if no price is available.
    """
    trade = await trade_repo.get_by_id(session, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=409, detail=f"Trade is already {trade.status}")

    if exit_price is None:
        mtm = await _latest_close_price(session, trade)
        if mtm is None:
            raise HTTPException(
                status_code=409,
                detail="No price bar available to mark-to-market close this trade",
            )
        exit_price = mtm

    pnl = compute_pnl(
        side=str(trade.side),
        size=float(trade.size_contracts),
        entry=float(trade.entry_price),
        exit_=float(exit_price),
        tick_value=await _resolve_tick_value(session, trade.instrument_id),
    )

    trade.exit_price = exit_price  # type: ignore[assignment]
    trade.closed_at = datetime.utcnow()
    trade.status = "closed"  # type: ignore[assignment]
    trade.outcome_pnl = pnl  # type: ignore[assignment]
    if reflection:
        trade.reflection = reflection  # type: ignore[assignment]
    await session.flush()
    return trade


# ---------------------------------------------------------------------------
# Equity curve
# ---------------------------------------------------------------------------
def _end_of_day(d: date) -> datetime:
    """End-of-day (23:59:59.999999) for the given calendar date, in UTC."""
    return datetime.combine(d, time(23, 59, 59, 999999), tzinfo=timezone.utc)


def _strip_tz(dt: datetime | None) -> datetime | None:
    """Return a naive UTC datetime if dt is tz-aware, else dt itself."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def _bars_for_contract_by_day(
    session: AsyncSession,
    contract_id: uuid.UUID,
    from_dt: datetime,
    to_dt: datetime,
) -> dict[date, float]:
    """Map calendar date → close for 1d bars between [from_dt, to_dt]."""
    result = await session.execute(
        select(PriceBar)
        .where(
            PriceBar.contract_id == contract_id,
            PriceBar.resolution == "1d",
            PriceBar.ts >= from_dt,
            PriceBar.ts <= to_dt,
        )
        .order_by(PriceBar.ts)
    )
    bars = list(result.scalars().all())
    return {b.ts.date(): float(b.close) for b in bars}


async def equity_curve(
    session: AsyncSession,
    since: date | None = None,
    user_id: uuid.UUID | None = None,
) -> list[dict]:
    """
    Daily equity series since `since` (default: 90 days ago) up to today (UTC).

    For each calendar day d:
      equity[d] = STARTING_EQUITY_USD
                + sum(outcome_pnl for closed trades with closed_at <= EOD(d))
                + sum(compute_pnl(side, size, entry, close@d) for trades
                       opened by EOD(d) AND still open at EOD(d))

    Open-position MTM uses the 1d bar `close` for the trade's bound contract,
    falling back to the instrument's front-month contract if no contract is bound.
    If no bar exists for a given day, the most recent prior close in the window
    is carried forward; if no prior close exists, the trade is skipped for that day.
    """
    today = datetime.now(timezone.utc).date()
    if since is None:
        since = today - timedelta(days=90)
    if since > today:
        return []

    # 1) Pre-load every trade once (scoped to the requester; None = anonymous pool).
    result = await session.execute(
        select(PaperTrade).where(PaperTrade.user_id == user_id)
    )
    all_trades: list[PaperTrade] = list(result.scalars().all())

    # 2) Pre-resolve a price-contract-id per trade (bound contract or instrument front-month).
    #    Then load all 1d bars in the window for each unique contract, keyed by date.
    front_month_cache: dict[uuid.UUID, uuid.UUID | None] = {}
    trade_price_contract: dict[uuid.UUID, uuid.UUID | None] = {}
    # B5: per-instrument tick value (contract_size) for the open-position MTM, cached
    # so each instrument is resolved once.
    tick_by_instrument: dict[uuid.UUID, float] = {}
    for t in all_trades:
        if t.instrument_id not in tick_by_instrument:
            tick_by_instrument[t.instrument_id] = await _resolve_tick_value(
                session, t.instrument_id
            )
        if t.contract_id is not None:
            trade_price_contract[t.id] = t.contract_id
            continue
        if t.instrument_id in front_month_cache:
            trade_price_contract[t.id] = front_month_cache[t.instrument_id]
            continue
        front = await contract_repo.get_front_month(session, t.instrument_id)
        front_id = front.id if front is not None else None
        front_month_cache[t.instrument_id] = front_id
        trade_price_contract[t.id] = front_id

    # PriceBar.ts is a naive Postgres TIMESTAMP column. asyncpg rejects a
    # tz-aware datetime against a naive column ("can't subtract offset-naive
    # and offset-aware datetimes"), so the bar-window bounds must be stripped
    # to naive UTC before binding.
    window_from = datetime.combine(since, time.min)
    window_to = datetime.combine(today, time(23, 59, 59, 999999))

    bars_by_contract: dict[uuid.UUID, dict[date, float]] = {}
    for cid in {c for c in trade_price_contract.values() if c is not None}:
        bars_by_contract[cid] = await _bars_for_contract_by_day(
            session, cid, window_from, window_to
        )

    # 3) Walk days from `since` to today.
    series: list[dict] = []
    cur = since
    while cur <= today:
        eod = _end_of_day(cur)
        eod_naive = eod.replace(tzinfo=None)

        realized = 0.0
        unrealized = 0.0

        for t in all_trades:
            opened_at = _strip_tz(t.opened_at)
            closed_at = _strip_tz(t.closed_at)
            if opened_at is None or opened_at > eod_naive:
                continue  # not yet opened

            is_closed_by_eod = (
                t.status == "closed"
                and closed_at is not None
                and closed_at <= eod_naive
            )
            if is_closed_by_eod:
                realized += float(t.outcome_pnl or 0.0)
                continue

            # Still open at EOD(cur). MTM off the day's close, or carry-forward.
            cid = trade_price_contract.get(t.id)
            if cid is None:
                continue
            day_close = _latest_close_at_or_before(bars_by_contract.get(cid, {}), cur)
            if day_close is None:
                continue
            unrealized += compute_pnl(
                side=str(t.side),
                size=float(t.size_contracts),
                entry=float(t.entry_price),
                exit_=day_close,
                tick_value=tick_by_instrument.get(t.instrument_id, NG_TICK_VALUE_USD),
            )

        equity = STARTING_EQUITY_USD + realized + unrealized
        series.append({"date": cur.isoformat(), "equity": round(equity, 2)})
        cur = cur + timedelta(days=1)

    return series


def _latest_close_at_or_before(
    bars_by_day: dict[date, float],
    d: date,
) -> float | None:
    """Return the close on day `d`, or the most recent close on a prior day in the map."""
    if not bars_by_day:
        return None
    if d in bars_by_day:
        return bars_by_day[d]
    prior_days = [k for k in bars_by_day.keys() if k <= d]
    if not prior_days:
        return None
    return bars_by_day[max(prior_days)]
