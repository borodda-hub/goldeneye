"""Tests MockMarketAdapter bar shape and OHLC invariants."""
import pytest
from datetime import datetime
from apps.api.adapters.market.mock import MockMarketAdapter

@pytest.fixture
def adapter():
    return MockMarketAdapter()

@pytest.mark.asyncio
async def test_get_bars_returns_list(adapter):
    from_dt = datetime(2025, 1, 1)
    to_dt = datetime(2026, 5, 10)
    bars = await adapter.get_bars("NGM26", "1d", from_dt, to_dt)
    assert len(bars) > 100, f"Expected >100 bars, got {len(bars)}"

@pytest.mark.asyncio
async def test_bar_shape(adapter):
    from_dt = datetime(2025, 1, 1)
    to_dt = datetime(2026, 5, 10)
    bars = await adapter.get_bars("NGM26", "1d", from_dt, to_dt)
    required_keys = {"ts", "contract_code", "resolution", "open", "high", "low", "close", "volume", "source"}
    for bar in bars[:5]:
        assert required_keys.issubset(bar.keys()), f"Missing keys: {required_keys - bar.keys()}"

@pytest.mark.asyncio
async def test_ohlc_invariants(adapter):
    from_dt = datetime(2025, 1, 1)
    to_dt = datetime(2026, 5, 10)
    bars = await adapter.get_bars("NGM26", "1d", from_dt, to_dt)
    for bar in bars[:100]:
        assert bar["high"] >= bar["open"], f"high < open: {bar}"
        assert bar["high"] >= bar["close"], f"high < close: {bar}"
        assert bar["low"] <= bar["open"], f"low > open: {bar}"
        assert bar["low"] <= bar["close"], f"low > close: {bar}"
        assert bar["high"] >= bar["low"], f"high < low: {bar}"

@pytest.mark.asyncio
async def test_get_latest_price(adapter):
    latest = await adapter.get_latest_price("NGM26")
    assert latest is not None
    assert "close" in latest
    assert latest["close"] > 0

@pytest.mark.asyncio
async def test_get_curve_snapshot(adapter):
    as_of = datetime(2026, 5, 9)
    curve = await adapter.get_curve_snapshot("NG", as_of)
    assert len(curve) == 12
    assert all("contract_code" in c and "mid_price" in c for c in curve)
