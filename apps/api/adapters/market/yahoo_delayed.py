"""Real (delayed ~15 min) market data adapter — Yahoo Finance chart API.

Why this and not the nasdaq.py stub: Nasdaq Data Link's CHRIS continuous
futures series is no longer free; Yahoo's public chart endpoint serves
the same delayed CME NG quotes at zero cost and zero auth. Trade-off:
unofficial API, can break without notice. Acceptable for a demo / single-user
research stack — the registry silent-falls-back to mock on error so the
dashboard never breaks even when Yahoo is unreachable.

Yahoo symbol convention:
    - "NG=F"             — continuous front-month NG futures
    - "NG{M}{YY}.NYM"    — a NYMEX-listed contract, e.g. "NGM26.NYM" = Jun 2026
    - "GC{M}{YY}.CMX"    — a COMEX-listed contract (metals: GC, SI)

When adding a new asset class, register its exchange suffix in
`_EXCHANGE_SUFFIX_BY_PREFIX` below.

Returns the same dict shape as MockMarketAdapter so the rest of the stack
(routers/dashboard.py, paper engine, ensemble) doesn't care which adapter
is selected.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

from apps.api.adapters._http import AdapterHTTPClient

logger = logging.getLogger(__name__)

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"

# Yahoo rejects requests without a browser-like User-Agent.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Goldeneye-research-terminal; +contact@example.com) "
        "Like-Gecko Chrome/120.0"
    ),
    "Accept": "application/json",
}

# Map our resolution → (Yahoo `interval`, default `range`).
# Yahoo restrictions:
#   - 1m bars: max range 7 days
#   - 5m / 15m / 1h bars: max range 60 days
#   - 1d bars: any range
_RESOLUTION_MAP: dict[str, tuple[str, str]] = {
    "1m": ("1m", "5d"),
    "5m": ("5m", "1mo"),
    "15m": ("15m", "1mo"),
    "1h": ("1h", "3mo"),
    "1d": ("1d", "1y"),
}

# CME futures month codes.
_MONTH_LETTERS = "FGHJKMNQUVXZ"  # Jan, Feb, ..., Dec

# Per-(contract, resolution) bar cache; 5 min TTL (Yahoo is 15-min delayed).
_CACHE_TTL_SECONDS = 5 * 60

# Yahoo's exchange-suffix convention varies by listing venue. Energy futures
# (NG, CL, HO, RB) are NYMEX; metals (GC, SI, HG) are COMEX. Adding a new
# commodity = adding one row here (or rely on the .NYM default if you don't
# know the listing yet — Yahoo will return empty for a wrong-suffix request,
# which surfaces as "no data" rather than a crash).
_EXCHANGE_SUFFIX_BY_PREFIX: dict[str, str] = {
    "NG": ".NYM",
    "CL": ".NYM",
    "HO": ".NYM",
    "RB": ".NYM",
    "GC": ".CMX",
    "SI": ".CMX",
    "HG": ".CMX",
}
_DEFAULT_EXCHANGE_SUFFIX = ".NYM"


def contract_to_yahoo_symbol(contract_code: str | None, symbol: str = "NG") -> str:
    """Map our contract_code to a Yahoo Finance ticker.

    Resolves the exchange suffix from the contract prefix (e.g. GCM26 → COMEX
    .CMX, NGM26 → NYMEX .NYM). Unknown prefixes fall back to .NYM — Yahoo
    will return an empty body for a wrong-listing request, which surfaces
    upstream as a quiet "no data" rather than a crash.

    Falls back to the continuous front-month "{SYMBOL}=F" when contract_code is
    empty or doesn't match our expected pattern.
    """
    if not contract_code:
        return f"{symbol}=F"
    code = contract_code.upper().strip()
    # Expected pattern: <prefix><month-letter><2-digit-year> e.g. NGM26 or GCM26
    if len(code) >= 4 and code[-3] in _MONTH_LETTERS and code[-2:].isdigit():
        prefix = code[:-3]
        suffix = _EXCHANGE_SUFFIX_BY_PREFIX.get(prefix, _DEFAULT_EXCHANGE_SUFFIX)
        return f"{code}{suffix}"
    # Fallback — treat as continuous front-month.
    return f"{symbol}=F"


def front_month_codes(symbol: str = "NG", start: date | None = None, count: int = 12) -> list[str]:
    """Generate the next `count` monthly futures contract codes starting from `start`.

    Used by get_curve_snapshot to enumerate the curve. Uses our internal code
    format (e.g., 'NGM26', not the Yahoo-suffixed form).
    """
    if start is None:
        start = date.today()
    codes: list[str] = []
    year = start.year
    month = start.month  # 1-indexed
    for _ in range(count):
        month_letter = _MONTH_LETTERS[month - 1]
        codes.append(f"{symbol}{month_letter}{year % 100:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return codes


def _expiry_for_code(contract_code: str) -> date | None:
    """Approximate the last-trading-day for an NG contract.

    NG futures expire 3 business days before the 1st calendar day of the
    delivery month. We use the last calendar day of the prior month as a
    reasonable display-grade expiry (consumers use it for ordering, not
    settlement math).
    """
    if len(contract_code) < 4:
        return None
    month_letter = contract_code[-3]
    year_digits = contract_code[-2:]
    if month_letter not in _MONTH_LETTERS or not year_digits.isdigit():
        return None
    month_idx = _MONTH_LETTERS.index(month_letter) + 1
    year = 2000 + int(year_digits)
    if month_idx == 1:
        return date(year - 1, 12, 31)
    delivery_first = date(year, month_idx, 1)
    return delivery_first - timedelta(days=1)


class YahooDelayedMarketAdapter:
    """Real MarketDataAdapter implementation reading Yahoo Finance (~15-min delayed)."""

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="market.yahoo_delayed")
        # Cache: (contract_code, resolution) → (cached_at, list[bar])
        self._bar_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}

    async def get_bars(
        self, contract_code: str, resolution: str, from_dt: datetime, to_dt: datetime
    ) -> list[dict[str, Any]]:
        bars = await self._get_bars_cached(contract_code, resolution)
        return [b for b in bars if from_dt <= b["ts"] <= to_dt]

    async def get_latest_price(self, contract_code: str) -> dict[str, Any] | None:
        # Prefer 1m bars for the most recent quote; fall back to 1d when the
        # market is closed and 1m returns nothing.
        bars = await self._get_bars_cached(contract_code, "1m")
        if not bars:
            bars = await self._get_bars_cached(contract_code, "1d")
        return bars[-1] if bars else None

    async def get_curve_snapshot(self, symbol: str, as_of: datetime) -> list[dict[str, Any]]:
        codes = front_month_codes(symbol=symbol, start=as_of.date(), count=12)
        # Pull latest 1d closes for each contract in parallel.
        results = await asyncio.gather(
            *(self._get_bars_cached(code, "1d") for code in codes),
            return_exceptions=True,
        )
        snapshot: list[dict[str, Any]] = []
        for code, bars_or_exc in zip(codes, results):
            if isinstance(bars_or_exc, BaseException) or not bars_or_exc:
                continue
            latest = bars_or_exc[-1]
            expiry = _expiry_for_code(code)
            snapshot.append(
                {
                    "contract_code": code,
                    "expiry": expiry.isoformat() if expiry else None,
                    "mid_price": latest["close"],
                }
            )
        return snapshot

    async def _get_bars_cached(self, contract_code: str, resolution: str) -> list[dict[str, Any]]:
        key = (contract_code, resolution)
        now = time.time()
        cached = self._bar_cache.get(key)
        if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
        try:
            bars = await self._fetch_bars(contract_code, resolution)
        except Exception as exc:
            logger.warning(
                "Yahoo fetch failed for %s @ %s: %s — returning empty.",
                contract_code,
                resolution,
                exc,
            )
            bars = []
        self._bar_cache[key] = (now, bars)
        return bars

    async def _fetch_bars(self, contract_code: str, resolution: str) -> list[dict[str, Any]]:
        interval, default_range = _RESOLUTION_MAP.get(resolution, _RESOLUTION_MAP["1d"])
        symbol = contract_to_yahoo_symbol(contract_code)
        url = YAHOO_BASE_URL + symbol
        params = {"interval": interval, "range": default_range, "includePrePost": "false"}
        response = await self._client.get(url, params=params, headers=_HEADERS)
        return _parse_chart(response.json(), contract_code, resolution)


def _parse_chart(body: dict, contract_code: str, resolution: str) -> list[dict[str, Any]]:
    """Parse Yahoo's chart envelope into our bar dict shape."""
    chart = body.get("chart") or {}
    error = chart.get("error")
    if error:
        logger.debug("Yahoo chart error for %s: %s", contract_code, error)
        return []
    result_list = chart.get("result") or []
    if not result_list:
        return []
    result = result_list[0]

    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote_list = indicators.get("quote") or []
    if not quote_list:
        return []
    quote = quote_list[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: list[dict[str, Any]] = []
    for i, ts_epoch in enumerate(timestamps):
        if i >= len(closes):
            break
        # Yahoo nulls out individual fields for missing bars (gaps).
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l_ = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None
        if None in (o, h, l_, c):
            continue
        bars.append(
            {
                "contract_code": contract_code,
                "resolution": resolution,
                "ts": datetime.utcfromtimestamp(int(ts_epoch)),
                "open": float(o),
                "high": float(h),
                "low": float(l_),
                "close": float(c),
                "volume": int(v) if v is not None else 0,
                "source": "yahoo_delayed",
            }
        )
    return bars
