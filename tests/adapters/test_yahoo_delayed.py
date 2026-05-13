"""Unit tests for the YahooDelayedMarketAdapter — symbol mapping, parsing, cache, curve."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.adapters.market.yahoo_delayed import (
    YahooDelayedMarketAdapter,
    _expiry_for_code,
    _parse_chart,
    contract_to_yahoo_symbol,
    front_month_codes,
)
from apps.api.adapters.base import MarketDataAdapter


# ── symbol mapping ────────────────────────────────────────────────────────


def test_contract_to_yahoo_symbol_appends_nym_for_known_contract():
    assert contract_to_yahoo_symbol("NGM26") == "NGM26.NYM"
    assert contract_to_yahoo_symbol("NGZ27") == "NGZ27.NYM"


def test_contract_to_yahoo_symbol_falls_back_to_continuous():
    assert contract_to_yahoo_symbol(None) == "NG=F"
    assert contract_to_yahoo_symbol("") == "NG=F"
    assert contract_to_yahoo_symbol("garbage") == "NG=F"


def test_contract_to_yahoo_symbol_honors_alternate_symbol():
    assert contract_to_yahoo_symbol(None, symbol="CL") == "CL=F"


def test_contract_to_yahoo_symbol_maps_cl_contracts():
    """WTI Crude monthly contract codes route to .NYM same as NG."""
    assert contract_to_yahoo_symbol("CLN26") == "CLN26.NYM"
    assert contract_to_yahoo_symbol("CLZ27") == "CLZ27.NYM"


def test_front_month_codes_for_cl_uses_cl_prefix():
    codes = front_month_codes(symbol="CL", start=date(2026, 5, 12), count=4)
    assert codes == ["CLK26", "CLM26", "CLN26", "CLQ26"]


def test_front_month_codes_enumerates_12_consecutive_months():
    codes = front_month_codes(start=date(2026, 5, 12), count=12)
    assert len(codes) == 12
    assert codes[0] == "NGK26"  # May 2026
    assert codes[1] == "NGM26"  # Jun 2026
    assert codes[7] == "NGZ26"  # Dec 2026
    assert codes[8] == "NGF27"  # Jan 2027 — year rollover


def test_front_month_codes_honors_count():
    codes = front_month_codes(start=date(2026, 1, 1), count=3)
    assert codes == ["NGF26", "NGG26", "NGH26"]


def test_expiry_for_code_is_last_day_of_prior_month():
    assert _expiry_for_code("NGM26") == date(2026, 5, 31)  # Jun delivery → May 31
    assert _expiry_for_code("NGF27") == date(2026, 12, 31)  # Jan delivery → Dec 31
    assert _expiry_for_code("NGZ26") == date(2026, 11, 30)  # Dec delivery → Nov 30


def test_expiry_for_code_rejects_malformed():
    assert _expiry_for_code("garbage") is None
    assert _expiry_for_code("NG") is None
    # Letter "B" is NOT a CME futures month letter — should be rejected.
    assert _expiry_for_code("NGB26") is None
    # Non-numeric year digits should also be rejected.
    assert _expiry_for_code("NGM2A") is None


# ── chart parsing ─────────────────────────────────────────────────────────


def _chart_body(timestamps: list[int], opens, highs, lows, closes, volumes) -> dict:
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": volumes,
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def test_parse_chart_maps_all_fields():
    body = _chart_body(
        [1735776000, 1735862400],
        [3.40, 3.41],
        [3.45, 3.46],
        [3.38, 3.39],
        [3.412, 3.42],
        [12345, 23456],
    )
    bars = _parse_chart(body, contract_code="NGM26", resolution="1d")
    assert len(bars) == 2
    bar = bars[0]
    assert bar["contract_code"] == "NGM26"
    assert bar["resolution"] == "1d"
    assert bar["open"] == 3.40
    assert bar["high"] == 3.45
    assert bar["low"] == 3.38
    assert bar["close"] == 3.412
    assert bar["volume"] == 12345
    assert bar["source"] == "yahoo_delayed"
    assert isinstance(bar["ts"], datetime)


def test_parse_chart_skips_null_bars():
    """Yahoo sometimes returns null for individual fields on gap days."""
    body = _chart_body(
        [1735776000, 1735862400],
        [3.40, None],
        [3.45, 3.46],
        [3.38, 3.39],
        [3.412, None],
        [12345, 0],
    )
    bars = _parse_chart(body, contract_code="NGM26", resolution="1d")
    assert len(bars) == 1
    assert bars[0]["open"] == 3.40


def test_parse_chart_handles_empty_response():
    assert _parse_chart({}, "NGM26", "1d") == []
    assert _parse_chart({"chart": {"result": []}}, "NGM26", "1d") == []


def test_parse_chart_handles_error_envelope():
    body = {"chart": {"error": {"code": "Not Found", "description": "..."}}}
    assert _parse_chart(body, "NGM26", "1d") == []


# ── adapter integration ──────────────────────────────────────────────────


def test_adapter_implements_protocol():
    assert isinstance(YahooDelayedMarketAdapter(), MarketDataAdapter)


def test_get_bars_filters_by_date_range():
    """Adapter returns naive UTC datetimes — test must build timestamps in UTC too."""
    from datetime import timezone
    adapter = YahooDelayedMarketAdapter()
    # UTC midnight on each of 5 consecutive days.
    base_utc = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    epochs = [int((base_utc + timedelta(days=i)).timestamp()) for i in range(5)]
    body = _chart_body(
        epochs,
        [3.0 + i * 0.01 for i in range(5)],
        [3.1 + i * 0.01 for i in range(5)],
        [2.9 + i * 0.01 for i in range(5)],
        [3.0 + i * 0.01 for i in range(5)],
        [1000 + i for i in range(5)],
    )

    class _FakeResponse:
        def json(self):
            return body

    with patch.object(adapter._client, "get", new=AsyncMock(return_value=_FakeResponse())):
        # Filter on naive-UTC datetimes (matches adapter's output).
        result = asyncio.run(
            adapter.get_bars(
                "NGM26",
                "1d",
                from_dt=datetime(2026, 5, 2, 0, 0, 0),
                to_dt=datetime(2026, 5, 4, 0, 0, 0),
            )
        )

    # Days 5/2, 5/3, 5/4 inclusive → three bars.
    assert len(result) == 3
    assert all(b["contract_code"] == "NGM26" for b in result)


def test_get_latest_price_returns_most_recent_bar():
    adapter = YahooDelayedMarketAdapter()
    base = datetime(2026, 5, 11, 9, 30, 0)
    body = _chart_body(
        [int((base + timedelta(minutes=i)).timestamp()) for i in range(3)],
        [3.40, 3.41, 3.42],
        [3.45, 3.46, 3.47],
        [3.38, 3.39, 3.40],
        [3.412, 3.42, 3.43],
        [100, 200, 300],
    )

    class _FakeResponse:
        def json(self):
            return body

    with patch.object(adapter._client, "get", new=AsyncMock(return_value=_FakeResponse())):
        latest = asyncio.run(adapter.get_latest_price("NGM26"))
        assert latest is not None
        assert latest["close"] == 3.43  # newest bar
        assert latest["resolution"] == "1m"  # latest path prefers 1m


def test_get_latest_price_falls_back_to_1d_when_1m_empty():
    """Outside market hours 1m may return no bars; fall back to 1d."""
    adapter = YahooDelayedMarketAdapter()
    call_log = {"intervals": []}

    body_empty = _chart_body([], [], [], [], [], [])
    body_daily = _chart_body(
        [int(datetime(2026, 5, 8).timestamp())],
        [3.40], [3.45], [3.38], [3.412], [12345],
    )

    async def fake_get(url, params=None, **_kw):
        interval = (params or {}).get("interval")
        call_log["intervals"].append(interval)
        class _Resp:
            def json(self):
                return body_empty if interval == "1m" else body_daily
        return _Resp()

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        latest = asyncio.run(adapter.get_latest_price("NGM26"))

    assert "1m" in call_log["intervals"]
    assert "1d" in call_log["intervals"]
    assert latest is not None
    assert latest["resolution"] == "1d"


def test_get_curve_snapshot_returns_12_contracts():
    adapter = YahooDelayedMarketAdapter()
    base_close = 3.0

    async def fake_get(url, params=None, **_kw):
        # Vary close price by URL so we know contracts are distinct.
        nonce = url[-10:]  # tail of URL
        body = _chart_body(
            [int(datetime(2026, 5, 8).timestamp())],
            [base_close], [base_close + 0.1], [base_close - 0.1], [base_close + hash(nonce) % 100 / 100],
            [12345],
        )
        class _Resp:
            def json(self):
                return body
        return _Resp()

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        snapshot = asyncio.run(adapter.get_curve_snapshot("NG", datetime(2026, 5, 12)))

    assert len(snapshot) == 12
    assert snapshot[0]["contract_code"] == "NGK26"
    assert snapshot[-1]["contract_code"].startswith("NG")
    assert all("mid_price" in s for s in snapshot)
    assert all("expiry" in s for s in snapshot)


def test_get_curve_snapshot_tolerates_individual_contract_failures():
    """If one contract's fetch errors, the snapshot still returns the others."""
    adapter = YahooDelayedMarketAdapter()

    body_ok = _chart_body(
        [int(datetime(2026, 5, 8).timestamp())], [3.0], [3.1], [2.9], [3.05], [12345]
    )

    call_count = {"n": 0}

    async def fake_get(url, params=None, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 3:
            raise RuntimeError("yahoo blew up for this one")
        class _Resp:
            def json(self):
                return body_ok
        return _Resp()

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        snapshot = asyncio.run(adapter.get_curve_snapshot("NG", datetime(2026, 5, 12)))

    # 12 attempts, 1 failed → 11 returned.
    assert len(snapshot) == 11


def test_cache_hits_avoid_second_http_call():
    adapter = YahooDelayedMarketAdapter()
    body = _chart_body([int(datetime(2026, 5, 8).timestamp())], [3.0], [3.1], [2.9], [3.05], [1000])

    class _Resp:
        def json(self):
            return body

    mock_get = AsyncMock(return_value=_Resp())
    with patch.object(adapter._client, "get", new=mock_get):
        asyncio.run(adapter.get_bars("NGM26", "1d", from_dt=datetime(2025, 1, 1), to_dt=datetime(2027, 1, 1)))
        asyncio.run(adapter.get_bars("NGM26", "1d", from_dt=datetime(2025, 1, 1), to_dt=datetime(2027, 1, 1)))
    assert mock_get.await_count == 1


def test_fetch_error_returns_empty_bars():
    """A network blow-up doesn't crash the request path — empty result + cached."""
    adapter = YahooDelayedMarketAdapter()
    async def boom(url, **_kw):
        raise RuntimeError("network down")
    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=boom)):
        bars = asyncio.run(adapter.get_bars("NGM26", "1d", from_dt=datetime(2025, 1, 1), to_dt=datetime(2027, 1, 1)))
    assert bars == []


def test_registry_returns_yahoo_when_selected(monkeypatch):
    from apps.api.adapters import registry
    from apps.api.src import settings as s

    registry.get_market.cache_clear()
    monkeypatch.setattr(s.settings, "adapter_market", "yahoo_delayed")
    instance = registry.get_market()
    registry.get_market.cache_clear()
    assert isinstance(instance, YahooDelayedMarketAdapter)
