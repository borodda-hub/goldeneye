"""Redis-backed cache for indicator compute calls (Phase 15 step 15a.2).

Wraps `base.compute` so identical (symbol, spec, time-window) requests serve
from Redis instead of recomputing. TTL is short (5 min default, configurable
via `settings.redis_ttl_chart_indicator`) so the live tail of the OHLCV
series doesn't go stale.

If Redis is unreachable the wrapper transparently falls through to direct
compute and logs a WARNING. Chart loads never block on cache health.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Protocol

import pandas as pd

from apps.api.services.indicators.base import IndicatorSeries, IndicatorSpec, compute
from apps.api.src.settings import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "chart:ind:"


class _AsyncCache(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: str, ex: int | None = None) -> Any: ...


def cache_key(
    symbol: str, spec: IndicatorSpec, from_ts: datetime, to_ts: datetime
) -> str:
    """Stable key per (symbol, type, sorted params, time window)."""
    payload = json.dumps(
        {
            "type": spec.type,
            "params": dict(sorted(spec.params.items())),
            "from": from_ts.isoformat(),
            "to": to_ts.isoformat(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{_KEY_PREFIX}{symbol}:{spec.type}:{digest}"


_default_client: _AsyncCache | None = None
_default_client_initialized = False


def _get_default_client() -> _AsyncCache | None:
    """Lazily build a redis.asyncio client from settings; cache the result.

    Returns None if redis-py isn't importable or `from_url` raises — callers
    just fall through to direct compute.
    """
    global _default_client, _default_client_initialized
    if _default_client_initialized:
        return _default_client
    _default_client_initialized = True
    try:
        from redis.asyncio import from_url

        _default_client = from_url(settings.redis_url, decode_responses=True)
    except Exception as e:  # pragma: no cover — defensive boot path
        logger.warning("indicators cache: redis init failed: %s", e)
        _default_client = None
    return _default_client


async def cached_compute(
    spec: IndicatorSpec,
    ohlcv: pd.DataFrame,
    *,
    symbol: str,
    from_ts: datetime,
    to_ts: datetime,
    client: _AsyncCache | None = None,
    ttl_sec: int | None = None,
) -> IndicatorSeries:
    """Serve `compute(spec, ohlcv)` through a Redis cache.

    Hits return the cached IndicatorSeries; misses compute, SETEX, and
    return fresh. Any Redis exception degrades to direct compute.
    """
    ttl = ttl_sec if ttl_sec is not None else settings.redis_ttl_chart_indicator
    cache = client if client is not None else _get_default_client()
    key = cache_key(symbol, spec, from_ts, to_ts)

    if cache is not None:
        try:
            raw = await cache.get(key)
            if raw is not None:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return IndicatorSeries.model_validate_json(raw)
        except Exception as e:
            logger.warning("indicators cache GET failed for %s: %s", key, e)

    series = compute(spec, ohlcv)

    if cache is not None:
        try:
            await cache.set(key, series.model_dump_json(), ex=ttl)
        except Exception as e:
            logger.warning("indicators cache SET failed for %s: %s", key, e)

    return series
