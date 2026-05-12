"""Unit tests for the delayed-quote poller — bar dedup, tick heartbeat, error tolerance."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.realtime import delayed_quote_poller


def _bar(ts: datetime, close: float = 3.412) -> dict:
    return {
        "ts": ts,
        "contract_code": "NGM26",
        "resolution": "1m",
        "open": close - 0.01,
        "high": close + 0.02,
        "low": close - 0.02,
        "close": close,
        "volume": 12345,
        "source": "yahoo_delayed",
    }


async def _step_loop_once(market_mock, broadcast_mock):
    """Run one iteration of _poll_loop and bail out before the sleep."""
    # Patch sleep to raise CancelledError after the first poll so the loop exits.
    sleep_calls = {"n": 0}

    async def fake_sleep(_secs):
        sleep_calls["n"] += 1
        raise asyncio.CancelledError()

    with patch.object(delayed_quote_poller, "get_market", return_value=market_mock), \
         patch.object(delayed_quote_poller, "broadcast", new=broadcast_mock), \
         patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(asyncio.CancelledError):
            await delayed_quote_poller._poll_loop()
    return sleep_calls["n"]


def test_emits_tick_every_poll():
    """The tick channel fires every poll, even if the bar timestamp hasn't moved."""
    ts = datetime(2026, 5, 11, 9, 30)
    market = type("M", (), {"get_latest_price": AsyncMock(return_value=_bar(ts))})()
    broadcast = AsyncMock()
    asyncio.run(_step_loop_once(market, broadcast))

    tick_calls = [c for c in broadcast.await_args_list if c.args[1] == "tick"]
    assert len(tick_calls) == 1
    payload = tick_calls[0].args[2]
    assert payload["contract_code"] == "NGM26"
    assert payload["price"] == 3.412
    assert payload["delayed"] is True


def test_emits_bar_when_timestamp_advances():
    """First poll emits a bar; the bar event payload mirrors the adapter's dict."""
    ts = datetime(2026, 5, 11, 9, 30)
    market = type("M", (), {"get_latest_price": AsyncMock(return_value=_bar(ts))})()
    broadcast = AsyncMock()
    asyncio.run(_step_loop_once(market, broadcast))

    bar_calls = [c for c in broadcast.await_args_list if c.args[1] == "bar"]
    assert len(bar_calls) == 1
    payload = bar_calls[0].args[2]
    assert payload["ts"] == ts.isoformat()
    assert payload["c"] == 3.412
    assert payload["delayed"] is True


def test_does_not_emit_duplicate_bars():
    """Two consecutive polls for the same bar ts → one tick each, one bar total."""
    ts = datetime(2026, 5, 11, 9, 30)

    async def step_two_polls(market_mock, broadcast_mock):
        sleep_calls = {"n": 0}

        async def fake_sleep(_secs):
            sleep_calls["n"] += 1
            if sleep_calls["n"] >= 2:
                raise asyncio.CancelledError()

        with patch.object(delayed_quote_poller, "get_market", return_value=market_mock), \
             patch.object(delayed_quote_poller, "broadcast", new=broadcast_mock), \
             patch("asyncio.sleep", new=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await delayed_quote_poller._poll_loop()

    market = type("M", (), {"get_latest_price": AsyncMock(return_value=_bar(ts))})()
    broadcast = AsyncMock()
    asyncio.run(step_two_polls(market, broadcast))

    bar_calls = [c for c in broadcast.await_args_list if c.args[1] == "bar"]
    tick_calls = [c for c in broadcast.await_args_list if c.args[1] == "tick"]
    assert len(bar_calls) == 1, "duplicate bars should be deduped"
    assert len(tick_calls) == 2, "tick should still fire every poll"


def test_emits_new_bar_when_timestamp_advances():
    """After the bar's ts moves forward, the next poll emits a fresh bar."""
    ts_a = datetime(2026, 5, 11, 9, 30)
    ts_b = datetime(2026, 5, 11, 9, 31)

    async def step_two_polls(market_mock, broadcast_mock):
        sleep_calls = {"n": 0}

        async def fake_sleep(_secs):
            sleep_calls["n"] += 1
            if sleep_calls["n"] >= 2:
                raise asyncio.CancelledError()

        with patch.object(delayed_quote_poller, "get_market", return_value=market_mock), \
             patch.object(delayed_quote_poller, "broadcast", new=broadcast_mock), \
             patch("asyncio.sleep", new=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await delayed_quote_poller._poll_loop()

    market = type(
        "M", (), {"get_latest_price": AsyncMock(side_effect=[_bar(ts_a, 3.40), _bar(ts_b, 3.41)])}
    )()
    broadcast = AsyncMock()
    asyncio.run(step_two_polls(market, broadcast))

    bar_calls = [c for c in broadcast.await_args_list if c.args[1] == "bar"]
    assert len(bar_calls) == 2


def test_adapter_error_does_not_kill_loop():
    """Errors from the adapter are swallowed, the loop continues to the next poll."""
    async def boom(_code):
        raise RuntimeError("yahoo went away")

    market = type("M", (), {"get_latest_price": boom})()
    broadcast = AsyncMock()
    asyncio.run(_step_loop_once(market, broadcast))

    # No emits because no data, but the sleep was reached → loop did not crash early.
    assert broadcast.await_count == 0


def test_handles_none_response():
    """If the adapter returns None, no broadcasts but the loop survives."""
    market = type("M", (), {"get_latest_price": AsyncMock(return_value=None)})()
    broadcast = AsyncMock()
    asyncio.run(_step_loop_once(market, broadcast))
    assert broadcast.await_count == 0
