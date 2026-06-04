"""Dashboard chyron tickers.

Two endpoints:
- /v1/ticker/quotes — curated macro basket prices (existing)
- /v1/ticker/news   — Bloomberg Markets RSS headlines (new)

Both are 5-min cached so the dashboard's polling doesn't hammer upstreams.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

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


# ─── News chyron ────────────────────────────────────────────────────────────

_BLOOMBERG_MARKETS_RSS = "https://feeds.bloomberg.com/markets/news.rss"
_NEWS_CACHE_TTL_SECONDS = 5 * 60
_news_cache: dict[str, Any] = {"ts": 0.0, "items": []}


def _parse_pub_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw.strip())
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    return None


@router.get("/news")
async def get_ticker_news() -> dict[str, Any]:
    """Bloomberg Markets RSS headlines for the secondary chyron."""
    now = time.time()
    if (now - float(_news_cache["ts"])) < _NEWS_CACHE_TTL_SECONDS and _news_cache["items"]:
        return {"items": _news_cache["items"], "source": "Bloomberg Markets", "cached": True}

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10.0) as client:
            resp = await client.get(_BLOOMBERG_MARKETS_RSS)
            xml_bytes = resp.content
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bloomberg ticker fetch failed: %s", exc)
        # Serve last good cache if we have one, even if stale.
        return {
            "items": _news_cache["items"],
            "source": "Bloomberg Markets",
            "cached": True,
            "stale": True,
        }

    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("Bloomberg RSS parse error: %s", exc)
        return {"items": _news_cache["items"], "source": "Bloomberg Markets", "cached": True, "stale": True}

    for el in root.iter("item"):
        title = (el.findtext("title") or "").strip()
        link = (el.findtext("link") or "").strip()
        pub = _parse_pub_date(el.findtext("pubDate"))
        if not title:
            continue
        items.append({"headline": title, "url": link or None, "published_at": pub})
        if len(items) >= 30:
            break

    _news_cache["ts"] = now
    _news_cache["items"] = items
    return {"items": items, "source": "Bloomberg Markets", "cached": False}
