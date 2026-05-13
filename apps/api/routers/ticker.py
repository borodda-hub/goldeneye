"""Dashboard chyron ticker — batched Yahoo quotes for a macro basket.

Curated symbol list — equities + commodities + macro — pulled in parallel from
Yahoo's chart endpoint (the same endpoint the market adapter uses for NG/CL).
A 5-min in-memory cache keeps Yahoo from getting hammered as the dashboard
refetches.

Returns the same minimal {symbol, name, last_price, change_pct} shape as the
watchlist endpoint so the frontend ticker can render with the same component
vocabulary as the watchlist sidebar.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/v1/ticker", tags=["ticker"])

logger = logging.getLogger(__name__)

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Goldeneye-research-terminal; +contact@example.com) "
        "Like-Gecko Chrome/120.0"
    ),
    "Accept": "application/json",
}

# Basket: ticker → display label.  Yahoo symbol on left, what the chyron shows
# on the right.  Order is the scroll order (left-to-right before the loop
# wraps).
BASKET: list[tuple[str, str]] = [
    # Equity indices
    ("^GSPC", "S&P 500"),
    ("^NDX", "Nasdaq 100"),
    ("^DJI", "Dow Jones"),
    ("^RUT", "Russell 2000"),
    ("^VIX", "VIX"),
    # Commodities
    ("NG=F", "Nat Gas"),
    ("CL=F", "WTI Crude"),
    ("HO=F", "Heating Oil"),
    ("RB=F", "RBOB Gas"),
    ("GC=F", "Gold"),
    ("SI=F", "Silver"),
    ("HG=F", "Copper"),
    ("ZC=F", "Corn"),
    ("ZS=F", "Soybeans"),
    ("ZW=F", "Wheat"),
    # Macro
    ("DX=F", "DXY"),
    ("^TNX", "10y Yield"),
]

# Yahoo is delayed ~15 min and Yahoo rate-limits aggressively. 5-min cache is
# generous and keeps the dashboard responsive.
_CACHE_TTL_SECONDS = 5 * 60
_cache: dict[str, Any] = {"ts": 0.0, "rows": []}


async def _fetch_one(client: httpx.AsyncClient, symbol: str) -> dict[str, Any] | None:
    """Hit Yahoo for the last two 1d bars on a symbol → derive last + change_pct.

    Returns None on any error so the caller can skip the row silently.
    """
    try:
        resp = await client.get(
            YAHOO_BASE_URL + symbol,
            params={"interval": "1d", "range": "5d", "includePrePost": "false"},
            headers=_HEADERS,
            timeout=8.0,
        )
        body = resp.json()
    except Exception as exc:
        logger.debug("ticker fetch failed for %s: %s", symbol, exc)
        return None

    chart = body.get("chart") or {}
    result_list = chart.get("result") or []
    if not result_list:
        return None
    result = result_list[0]
    indicators = result.get("indicators") or {}
    quote_list = indicators.get("quote") or []
    if not quote_list:
        return None
    closes = quote_list[0].get("close") or []
    closes = [c for c in closes if c is not None]
    if not closes:
        return None
    last = float(closes[-1])
    prev = float(closes[-2]) if len(closes) >= 2 else last
    change_pct = (last / prev) - 1.0 if prev else 0.0
    return {"last_price": last, "change_pct": change_pct, "prev_close": prev}


@router.get("/quotes")
async def get_ticker_quotes() -> dict[str, Any]:
    """Return the curated basket with last + change_pct for each symbol."""
    now = time.time()
    if (now - float(_cache["ts"])) < _CACHE_TTL_SECONDS and _cache["rows"]:
        return {"items": _cache["rows"], "cached": True}

    async with httpx.AsyncClient(headers=_HEADERS) as client:
        results = await asyncio.gather(
            *(_fetch_one(client, sym) for sym, _ in BASKET),
            return_exceptions=False,
        )

    items: list[dict[str, Any]] = []
    for (symbol, label), quote in zip(BASKET, results):
        items.append(
            {
                "symbol": symbol,
                "label": label,
                "last_price": quote["last_price"] if quote else None,
                "change_pct": quote["change_pct"] if quote else None,
            }
        )
    _cache["ts"] = now
    _cache["rows"] = items
    return {"items": items, "cached": False}
