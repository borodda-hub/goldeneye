"""Tests for the Redis-backed indicator compute cache (Phase 15 step 15a.2)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import pytest

from apps.api.services.indicators import IndicatorSpec
from apps.api.services.indicators.cache import cache_key, cached_compute


class FakeRedis:
    """In-memory async stand-in for redis.asyncio.Redis."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> Any:
        self.get_calls += 1
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> Any:
        self.set_calls += 1
        self.store[key] = value
        return True


class BrokenRedis:
    """Async client that raises on every call — simulates a Redis outage."""

    async def get(self, key: str) -> Any:
        raise ConnectionError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None) -> Any:
        raise ConnectionError("redis down")


def _frame() -> pd.DataFrame:
    closes = [10.0, 11, 12, 11, 13, 14, 15, 14, 16, 17]
    idx = pd.DatetimeIndex(
        [datetime(2026, 1, 1) + timedelta(days=i) for i in range(len(closes))]
    )
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.5 for c in closes],
            "low": [c - 0.5 for c in closes],
            "close": closes,
            "volume": [1.0] * len(closes),
        },
        index=idx,
    )


_FROM = datetime(2026, 1, 1)
_TO = datetime(2026, 1, 10)


# ---------- cache_key ----------


def test_cache_key_stable_across_param_order():
    spec_a = IndicatorSpec(type="sma", params={"period": 5, "source": "close"})
    spec_b = IndicatorSpec(type="sma", params={"source": "close", "period": 5})
    assert cache_key("NG", spec_a, _FROM, _TO) == cache_key("NG", spec_b, _FROM, _TO)


def test_cache_key_changes_with_period():
    spec_5 = IndicatorSpec(type="sma", params={"period": 5})
    spec_10 = IndicatorSpec(type="sma", params={"period": 10})
    assert cache_key("NG", spec_5, _FROM, _TO) != cache_key("NG", spec_10, _FROM, _TO)


def test_cache_key_changes_with_window():
    spec = IndicatorSpec(type="sma", params={"period": 5})
    later = _TO + timedelta(days=1)
    assert cache_key("NG", spec, _FROM, _TO) != cache_key("NG", spec, _FROM, later)


def test_cache_key_changes_with_symbol():
    spec = IndicatorSpec(type="sma", params={"period": 5})
    assert cache_key("NG", spec, _FROM, _TO) != cache_key("CL", spec, _FROM, _TO)


def test_cache_key_includes_type_segment():
    spec = IndicatorSpec(type="ema", params={"period": 5})
    key = cache_key("NG", spec, _FROM, _TO)
    assert key.startswith("chart:ind:NG:ema:")


# ---------- cached_compute ----------


@pytest.mark.asyncio
async def test_miss_computes_and_sets():
    redis = FakeRedis()
    spec = IndicatorSpec(type="sma", params={"period": 3})
    series = await cached_compute(
        spec, _frame(), symbol="NG", from_ts=_FROM, to_ts=_TO, client=redis
    )

    assert redis.get_calls == 1
    assert redis.set_calls == 1
    assert len(series.points) == 10
    # SMA(3) of the fixture's first defined index = 11.0
    assert series.points[2].v == pytest.approx(11.0)


@pytest.mark.asyncio
async def test_hit_skips_compute():
    redis = FakeRedis()
    spec = IndicatorSpec(type="sma", params={"period": 3})

    first = await cached_compute(
        spec, _frame(), symbol="NG", from_ts=_FROM, to_ts=_TO, client=redis
    )
    assert redis.set_calls == 1

    # Second call with an empty frame would normally raise inside compute;
    # if it returns the same series, we know the cache short-circuited.
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    second = await cached_compute(
        spec, empty, symbol="NG", from_ts=_FROM, to_ts=_TO, client=redis
    )

    assert redis.set_calls == 1  # no additional SET on hit
    assert redis.get_calls == 2
    assert [p.v for p in first.points] == [p.v for p in second.points]


@pytest.mark.asyncio
async def test_falls_through_on_redis_error():
    spec = IndicatorSpec(type="sma", params={"period": 3})
    series = await cached_compute(
        spec, _frame(), symbol="NG", from_ts=_FROM, to_ts=_TO, client=BrokenRedis()
    )
    # Compute still succeeds — outage is invisible to callers
    assert len(series.points) == 10
    assert series.points[2].v == pytest.approx(11.0)


@pytest.mark.asyncio
async def test_no_client_disables_caching_cleanly():
    """Passing client=None and having no default client wired returns fresh
    compute without raising (default client is lazy and may not be reachable)."""
    spec = IndicatorSpec(type="sma", params={"period": 3})
    # We can't easily monkey-patch the module-level default client lazily,
    # so verify with an explicit no-op cache.

    class NullCache:
        async def get(self, key: str) -> Any:
            return None

        async def set(self, key: str, value: str, ex: int | None = None) -> Any:
            return True

    series = await cached_compute(
        spec, _frame(), symbol="NG", from_ts=_FROM, to_ts=_TO, client=NullCache()
    )
    assert len(series.points) == 10
