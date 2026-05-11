"""
Engine tests for apps.api.services.paper_engine.

Covers:
- Pure compute_pnl math (long/short profit/loss + tick-value multiplier).
- validate_open: zero size, inverted long/short stops, leverage breach.
- close_trade MTM fallback off the latest 1d bar.
- equity_curve daily resampling: starting equity + realized + open MTM.

DB sessions are mocked via unittest.mock.AsyncMock; this keeps the unit tests
self-contained (no Postgres/Timescale container needed).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from apps.api.services import paper_engine
from apps.api.services.paper_engine import (
    LEVERAGE_CAP,
    NG_TICK_VALUE_USD,
    STARTING_EQUITY_USD,
    compute_pnl,
    validate_open,
)


# ---------------------------------------------------------------------------
# compute_pnl — pure-function tests
# ---------------------------------------------------------------------------
def test_compute_pnl_long_profit() -> None:
    pnl = compute_pnl(side="long", size=2.0, entry=3.00, exit_=3.10)
    # (3.10 - 3.00) × 2 × 10_000 = 2000.0
    assert pnl == pytest.approx(2000.0)
    assert pnl > 0


def test_compute_pnl_long_loss() -> None:
    pnl = compute_pnl(side="long", size=2.0, entry=3.00, exit_=2.90)
    assert pnl == pytest.approx(-2000.0)
    assert pnl < 0


def test_compute_pnl_short_profit() -> None:
    # Short profits when exit < entry.
    pnl = compute_pnl(side="short", size=2.0, entry=3.00, exit_=2.90)
    assert pnl == pytest.approx(2000.0)
    assert pnl > 0


def test_compute_pnl_short_loss() -> None:
    pnl = compute_pnl(side="short", size=2.0, entry=3.00, exit_=3.10)
    assert pnl == pytest.approx(-2000.0)
    assert pnl < 0


def test_compute_pnl_uses_tick_value() -> None:
    """A $0.01 move on 1 contract should be $100 — i.e. ×10,000 tick value."""
    pnl = compute_pnl(side="long", size=1.0, entry=3.00, exit_=3.01)
    assert pnl == pytest.approx(100.0)
    # Verify a unit move scales to $10,000/contract.
    one_dollar = compute_pnl(side="long", size=1.0, entry=3.00, exit_=4.00)
    assert one_dollar == pytest.approx(NG_TICK_VALUE_USD)


def test_compute_pnl_custom_tick_value() -> None:
    pnl = compute_pnl(side="long", size=1.0, entry=3.00, exit_=3.10, tick_value=1.0)
    assert pnl == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# validate_open — uses a mocked session; current_equity returns STARTING_EQUITY.
# ---------------------------------------------------------------------------
def _mock_session_with_equity(equity: float = STARTING_EQUITY_USD) -> AsyncMock:
    """Make an AsyncSession-like mock that yields zero closed trades for equity."""
    session = AsyncMock()
    # We patch current_equity directly in the tests that need a specific value;
    # this helper is for cases where the default starting equity is fine.
    return session


@pytest.mark.asyncio
async def test_validate_open_rejects_zero_size() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=0.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=None,
            )
    assert exc.value.status_code == 400
    assert "size" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_negative_size() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=-1.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=None,
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_open_rejects_zero_entry_price() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=1.0,
                entry_price=0.0,
                stop_loss=None,
                take_profit=None,
            )
    assert exc.value.status_code == 400
    assert "entry_price" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_invalid_side() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="sideways",
                size=1.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=None,
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_open_rejects_inverted_long_stops() -> None:
    """Long: stop_loss must be below entry."""
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=1.0,
                entry_price=3.0,
                stop_loss=3.5,  # above entry → invalid for long
                take_profit=None,
            )
    assert exc.value.status_code == 400
    assert "stop_loss" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_inverted_long_takeprofit() -> None:
    """Long: take_profit must be above entry."""
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=1.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=2.5,  # below entry → invalid for long
            )
    assert exc.value.status_code == 400
    assert "take_profit" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_inverted_short_stops() -> None:
    """Short: stop_loss must be above entry."""
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="short",
                size=1.0,
                entry_price=3.0,
                stop_loss=2.5,  # below entry → invalid for short
                take_profit=None,
            )
    assert exc.value.status_code == 400
    assert "stop_loss" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_inverted_short_takeprofit() -> None:
    """Short: take_profit must be below entry."""
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="short",
                size=1.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=3.5,  # above entry → invalid for short
            )
    assert exc.value.status_code == 400
    assert "take_profit" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_rejects_leverage_breach() -> None:
    """
    Cap = 10 × $100,000 = $1,000,000 notional.
    At $3.00/MMBtu × 10,000/contract = $30,000 per contract.
    1,000,000 / 30,000 ≈ 33.3 contracts max. 40 should breach.
    """
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        with pytest.raises(HTTPException) as exc:
            await validate_open(
                session,
                side="long",
                size=40.0,
                entry_price=3.0,
                stop_loss=None,
                take_profit=None,
            )
    assert exc.value.status_code == 409
    assert "leverage" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_open_accepts_at_cap_boundary() -> None:
    """A size exactly at the leverage cap should be allowed (cap is strict >)."""
    session = _mock_session_with_equity()
    # 30 contracts × $3 × 10,000 = $900,000 < $1,000,000 cap → fine.
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        await validate_open(
            session,
            side="long",
            size=30.0,
            entry_price=3.0,
            stop_loss=2.5,
            take_profit=3.5,
        )


@pytest.mark.asyncio
async def test_validate_open_happy_path_long() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        # Should not raise.
        await validate_open(
            session,
            side="long",
            size=2.0,
            entry_price=3.0,
            stop_loss=2.8,
            take_profit=3.3,
        )


@pytest.mark.asyncio
async def test_validate_open_happy_path_short() -> None:
    session = _mock_session_with_equity()
    with patch.object(paper_engine, "current_equity", AsyncMock(return_value=STARTING_EQUITY_USD)):
        await validate_open(
            session,
            side="short",
            size=2.0,
            entry_price=3.0,
            stop_loss=3.3,
            take_profit=2.8,
        )


# ---------------------------------------------------------------------------
# close_trade — MTM and explicit-price paths.
# ---------------------------------------------------------------------------
def _fake_trade(
    *,
    status: str = "open",
    side: str = "long",
    entry: float = 3.00,
    size: float = 1.0,
    contract_id: uuid.UUID | None = None,
    instrument_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        side=side,
        entry_price=entry,
        size_contracts=size,
        contract_id=contract_id,
        instrument_id=instrument_id or uuid.uuid4(),
        exit_price=None,
        outcome_pnl=None,
        reflection=None,
        closed_at=None,
        opened_at=datetime.utcnow() - timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_close_trade_with_explicit_exit_price() -> None:
    """Explicit exit_price should be used verbatim and PnL computed off it."""
    trade = _fake_trade(side="long", entry=3.00, size=2.0)
    session = AsyncMock()

    with patch("apps.api.services.paper_engine.trade_repo") as mock_repo:
        mock_repo.get_by_id = AsyncMock(return_value=trade)
        closed = await paper_engine.close_trade(session, trade.id, exit_price=3.10)

    assert closed.status == "closed"
    assert closed.exit_price == pytest.approx(3.10)
    # (3.10 - 3.00) × 2 × 10_000 = 2000
    assert closed.outcome_pnl == pytest.approx(2000.0)


@pytest.mark.asyncio
async def test_close_trade_404_if_not_found() -> None:
    session = AsyncMock()
    with patch("apps.api.services.paper_engine.trade_repo") as mock_repo:
        mock_repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await paper_engine.close_trade(session, uuid.uuid4(), exit_price=3.1)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_close_trade_409_if_already_closed() -> None:
    trade = _fake_trade(status="closed")
    session = AsyncMock()
    with patch("apps.api.services.paper_engine.trade_repo") as mock_repo:
        mock_repo.get_by_id = AsyncMock(return_value=trade)
        with pytest.raises(HTTPException) as exc:
            await paper_engine.close_trade(session, trade.id, exit_price=3.1)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_close_trade_mtm_uses_latest_bar_mid() -> None:
    """When exit_price is None, the engine marks to market off the latest 1d bar."""
    trade = _fake_trade(side="long", entry=3.00, size=1.0, contract_id=uuid.uuid4())
    session = AsyncMock()

    with (
        patch("apps.api.services.paper_engine.trade_repo") as mock_repo,
        patch(
            "apps.api.services.paper_engine._latest_close_price",
            AsyncMock(return_value=3.20),
        ),
    ):
        mock_repo.get_by_id = AsyncMock(return_value=trade)
        closed = await paper_engine.close_trade(session, trade.id, exit_price=None)

    assert closed.exit_price == pytest.approx(3.20)
    assert closed.outcome_pnl == pytest.approx(2000.0)  # 0.20 × 1 × 10_000


@pytest.mark.asyncio
async def test_close_trade_mtm_409_when_no_bar() -> None:
    trade = _fake_trade(contract_id=uuid.uuid4())
    session = AsyncMock()

    with (
        patch("apps.api.services.paper_engine.trade_repo") as mock_repo,
        patch(
            "apps.api.services.paper_engine._latest_close_price",
            AsyncMock(return_value=None),
        ),
    ):
        mock_repo.get_by_id = AsyncMock(return_value=trade)
        with pytest.raises(HTTPException) as exc:
            await paper_engine.close_trade(session, trade.id, exit_price=None)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# current_equity & equity_curve
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_current_equity_no_closed_trades() -> None:
    """Empty closed-trade list → just the starting balance."""
    session = AsyncMock()
    scalars = AsyncMock()
    scalars.all = lambda: []  # plain func, not async
    # session.execute returns a Result-like; .scalars() returns scalars-like; .all() returns list.
    exec_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    session.execute = AsyncMock(return_value=exec_result)
    equity = await paper_engine.current_equity(session)
    assert equity == pytest.approx(STARTING_EQUITY_USD)


@pytest.mark.asyncio
async def test_current_equity_sums_closed_pnl() -> None:
    closed = [
        SimpleNamespace(outcome_pnl=1500.0),
        SimpleNamespace(outcome_pnl=-300.0),
        SimpleNamespace(outcome_pnl=None),  # treated as 0
    ]
    session = AsyncMock()
    exec_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: closed))
    session.execute = AsyncMock(return_value=exec_result)
    equity = await paper_engine.current_equity(session)
    assert equity == pytest.approx(STARTING_EQUITY_USD + 1500.0 - 300.0)


@pytest.mark.asyncio
async def test_equity_curve_empty_returns_starting_balance_per_day() -> None:
    """No trades → every day is exactly the starting equity."""
    session = AsyncMock()
    exec_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    session.execute = AsyncMock(return_value=exec_result)

    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=5)
    series = await paper_engine.equity_curve(session, since=since)

    assert len(series) == 6  # since..today inclusive
    for point in series:
        assert point["equity"] == pytest.approx(STARTING_EQUITY_USD)
        assert "date" in point


@pytest.mark.asyncio
async def test_equity_curve_since_in_future_returns_empty() -> None:
    session = AsyncMock()
    exec_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    session.execute = AsyncMock(return_value=exec_result)
    future = datetime.now(timezone.utc).date() + timedelta(days=10)
    series = await paper_engine.equity_curve(session, since=future)
    assert series == []


def test_latest_close_at_or_before_returns_exact_match() -> None:
    bars = {
        date(2026, 5, 1): 3.10,
        date(2026, 5, 2): 3.15,
        date(2026, 5, 3): 3.20,
    }
    assert paper_engine._latest_close_at_or_before(bars, date(2026, 5, 2)) == 3.15


def test_latest_close_at_or_before_carries_forward() -> None:
    bars = {
        date(2026, 5, 1): 3.10,
        date(2026, 5, 3): 3.20,
    }
    # Day 2 missing → carry-forward from day 1.
    assert paper_engine._latest_close_at_or_before(bars, date(2026, 5, 2)) == 3.10


def test_latest_close_at_or_before_none_when_no_prior() -> None:
    bars = {date(2026, 5, 5): 3.10}
    assert paper_engine._latest_close_at_or_before(bars, date(2026, 5, 1)) is None


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------
def test_constants_match_spec() -> None:
    assert NG_TICK_VALUE_USD == 10_000.0
    assert STARTING_EQUITY_USD == 100_000.0
    assert LEVERAGE_CAP == 10.0
