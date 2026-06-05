"""List instruments + their current quote (Phase 14 step 6).

Powers the dashboard watchlist sidebar. Each row carries enough data to
render: symbol, name, last price, change vs prior close, vol regime.
Live quotes come from the same dashboard pipeline so the watchlist
stays consistent with what's shown on whichever instrument is active.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.services.price_lookup import get_latest_closes
from apps.api.src.settings import settings

router = APIRouter(prefix="/v1/instruments", tags=["instruments"])

logger = logging.getLogger(__name__)

# The watchlist fans out one live market-adapter call per symbol (26×), so the
# uncached endpoint is ~1.5s. The same payload is identical for every client,
# and the underlying quotes are 15-min delayed, so a short shared Redis cache
# makes repeat loads near-instant without meaningfully staling the data.
_WATCHLIST_CACHE_KEY = "watchlist:v1"
_WATCHLIST_TTL_SEC = 30

_redis_client: Any = None
_redis_initialized = False


def _get_cache() -> Any:
    """Lazy redis.asyncio client; None if unavailable (callers fall through)."""
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client
    _redis_initialized = True
    try:
        from redis.asyncio import from_url

        _redis_client = from_url(settings.redis_url, decode_responses=True)
    except Exception as e:  # pragma: no cover — defensive boot path
        logger.warning("watchlist cache: redis init failed: %s", e)
        _redis_client = None
    return _redis_client


@router.get("")
async def list_instruments(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return every seeded instrument with a thin quote attached.

    Quote derivation:
      last_price  ← front month's latest 1d bar close
      change_abs  ← close - previous close
      change_pct  ← change_abs / previous close
    Falls back to nulls when the contract has no bars yet — UI renders
    a placeholder rather than crashing.
    """
    cache = _get_cache()
    if cache is not None:
        try:
            raw = await cache.get(_WATCHLIST_CACHE_KEY)
            if raw:
                return dict(json.loads(raw))
        except Exception as e:
            logger.warning("watchlist cache GET failed: %s", e)

    rows = await instr_repo.get_all(session)
    out: list[dict[str, Any]] = []
    for instrument in rows:
        front = await contract_repo.get_front_month(session, instrument.id)
        quote: dict[str, Any] = {
            "last_price": None,
            "change_abs": None,
            "change_pct": None,
            "front_month_code": front.contract_code if front else None,
            "as_of": None,
        }
        if front is not None:
            closes = await get_latest_closes(
                session,
                contract_id=front.id,
                contract_code=front.contract_code,
                n=2,
            )
            # closes is oldest-first; "last" close is the most recent.
            if len(closes) >= 1:
                quote["last_price"] = float(closes[-1])
            if len(closes) >= 2 and closes[-2]:
                prev = float(closes[-2])
                last = float(closes[-1])
                delta = last - prev
                quote["change_abs"] = delta
                quote["change_pct"] = delta / prev if prev else None

        out.append(
            {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "asset_class": instrument.asset_class,
                "currency": instrument.currency,
                "unit": instrument.unit,
                # ORM column is `metadata_` to avoid the DeclarativeBase
                # name clash; surface it as `metadata` in the API.
                "metadata": instrument.metadata_ or {},
                "quote": quote,
            }
        )
    # Stable order: NG first, then alphabetic for the rest. Predictable
    # for tests and for the UI which depends on the array index.
    out.sort(key=lambda r: (0 if r["symbol"] == "NG" else 1, r["symbol"]))
    result = {"instruments": out}

    if cache is not None:
        try:
            await cache.set(
                _WATCHLIST_CACHE_KEY, json.dumps(result), ex=_WATCHLIST_TTL_SEC
            )
        except Exception as e:
            logger.warning("watchlist cache SET failed: %s", e)

    return result
