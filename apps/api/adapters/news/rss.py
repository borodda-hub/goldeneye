"""Real NewsDataAdapter — pulls per-instrument headlines from public RSS feeds.

Sources (free, no auth):
  NG:
    - EIA "Today in Energy"      — https://www.eia.gov/todayinenergy/rss.xml
    - Yahoo Finance NG=F          — feeds.finance.yahoo.com/rss/2.0/headline?s=NG=F
    - NWS active alerts (TX/LA/PA/NY/OK/OH/MI/IL) — gas-demand state weather
  CL:
    - EIA "Today in Energy"      — same EIA feed; filtered with CL keywords
    - Yahoo Finance CL=F          — feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F
    - OilPrice.com               — https://oilprice.com/rss/main

Items are filtered by the symbol's keyword list (case-insensitive substring
match on title or description). Results carry an extra `url` field that the
mock adapter doesn't — consumers that don't read it ignore it.

No DB persistence. The adapter fetches RSS on demand, caches for 10 min,
and returns dicts in the same shape as MockNewsAdapter.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

from apps.api.adapters._http import AdapterHTTPClient

logger = logging.getLogger(__name__)

# Feed format: "rss" → RSS 2.0 with <item> elements; "atom" → Atom with <entry>.
FeedSpec = tuple[str, str]  # (url, format)


class SymbolNewsConfig:
    """Per-instrument news pipeline configuration.

    Bundles the feed list, keyword filter, accept-all sources (those skipping
    the keyword check), per-source default categories, and per-source caps.
    """

    __slots__ = (
        "feeds",
        "keywords",
        "accept_all_sources",
        "default_categories",
        "source_caps",
    )

    def __init__(
        self,
        feeds: dict[str, FeedSpec],
        keywords: list[str],
        accept_all_sources: frozenset[str] = frozenset(),
        default_categories: dict[str, str] | None = None,
        source_caps: dict[str, int] | None = None,
    ):
        self.feeds = feeds
        self.keywords = keywords
        self.accept_all_sources = accept_all_sources
        self.default_categories = default_categories or {}
        self.source_caps = source_caps or {}


# ── NG (natural gas) configuration ────────────────────────────────────────

_NG_CONFIG = SymbolNewsConfig(
    feeds={
        "eia_today_in_energy": (
            "https://www.eia.gov/todayinenergy/rss.xml",
            "rss",
        ),
        "yahoo_finance_ng": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NG=F&region=US&lang=en-US",
            "rss",
        ),
        # NWS active alerts across the major gas-demand states. Atom feed.
        "nws_alerts": (
            "https://api.weather.gov/alerts/active.atom?area=TX,LA,PA,NY,OK,OH,MI,IL,PA",
            "atom",
        ),
    },
    keywords=[
        "natural gas",
        "natgas",
        "lng",
        "henry hub",
        "eia storage",
        "haynesville",
        "appalachian gas",
        "permian gas",
        "ng futures",
        "winter heating",
        "pipeline",
    ],
    # NWS region-scoped alerts are inherently gas-demand-relevant — skip the
    # keyword filter for that source.
    accept_all_sources=frozenset({"nws_alerts"}),
    default_categories={"nws_alerts": "weather"},
    source_caps={"nws_alerts": 5},
)


# ── CL (WTI crude oil) configuration ──────────────────────────────────────

_CL_CONFIG = SymbolNewsConfig(
    feeds={
        "eia_today_in_energy": (
            "https://www.eia.gov/todayinenergy/rss.xml",
            "rss",
        ),
        "yahoo_finance_cl": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F&region=US&lang=en-US",
            "rss",
        ),
        "oilprice_main": ("https://oilprice.com/rss/main", "rss"),
    },
    keywords=[
        "crude oil",
        "crude",
        "wti",
        "brent",
        "opec",
        "refinery",
        "refining",
        "distillate",
        "gasoline",
        "cushing",
        "spr",
        "petroleum",
        "drilling",
        "rig count",
    ],
)


# ── HO (heating oil / distillate) configuration ───────────────────────────

_HO_CONFIG = SymbolNewsConfig(
    feeds={
        "eia_today_in_energy": ("https://www.eia.gov/todayinenergy/rss.xml", "rss"),
        "yahoo_finance_ho": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=HO=F&region=US&lang=en-US",
            "rss",
        ),
        "oilprice_main": ("https://oilprice.com/rss/main", "rss"),
    },
    keywords=[
        "heating oil",
        "distillate",
        "diesel",
        "ulsd",
        "crack spread",
        "refinery",
        "refining",
        "winter demand",
        "winter heating",
    ],
    accept_all_sources=frozenset({"yahoo_finance_ho"}),
)


# ── RB (RBOB gasoline) configuration ──────────────────────────────────────

_RB_CONFIG = SymbolNewsConfig(
    feeds={
        "eia_today_in_energy": ("https://www.eia.gov/todayinenergy/rss.xml", "rss"),
        "yahoo_finance_rb": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=RB=F&region=US&lang=en-US",
            "rss",
        ),
        "oilprice_main": ("https://oilprice.com/rss/main", "rss"),
    },
    keywords=[
        "gasoline",
        "rbob",
        "refinery",
        "refining",
        "crack spread",
        "driving season",
        "pump price",
        "summer blend",
    ],
    accept_all_sources=frozenset({"yahoo_finance_rb"}),
)


# ── GC (gold) configuration ───────────────────────────────────────────────

_GC_CONFIG = SymbolNewsConfig(
    feeds={
        "yahoo_finance_gc": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US",
            "rss",
        ),
        # Kitco metals news — feed URL verified live in 17g; on fetch failure
        # the Yahoo source still carries the card.
        "kitco_news": ("https://www.kitco.com/rss/KitcoNews.xml", "rss"),
    },
    keywords=[
        "gold",
        "bullion",
        "fomc",
        "federal reserve",
        "dollar",
        "dxy",
        "real yields",
        "safe haven",
        "central bank",
    ],
    accept_all_sources=frozenset({"yahoo_finance_gc"}),
)


# ── SI (silver) configuration ─────────────────────────────────────────────

_SI_CONFIG = SymbolNewsConfig(
    feeds={
        "yahoo_finance_si": (
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SI=F&region=US&lang=en-US",
            "rss",
        ),
        "kitco_news": ("https://www.kitco.com/rss/KitcoNews.xml", "rss"),
    },
    keywords=[
        "silver",
        "bullion",
        "industrial demand",
        "solar",
        "gold-silver ratio",
        "fomc",
        "real yields",
    ],
    accept_all_sources=frozenset({"yahoo_finance_si"}),
)


SYMBOL_CONFIGS: dict[str, SymbolNewsConfig] = {
    "NG": _NG_CONFIG,
    "CL": _CL_CONFIG,
    "HO": _HO_CONFIG,
    "RB": _RB_CONFIG,
    "GC": _GC_CONFIG,
    "SI": _SI_CONFIG,
}


def _make_default_config(symbol: str) -> SymbolNewsConfig:
    """Generic per-symbol config for any instrument we haven't curated keyword
    lists for — including the B5 cross-asset classes (index/rates, e.g. ES/ZN).
    There is NO curated keyword taxonomy for these: it uses Yahoo Finance's
    per-symbol headline RSS (already filtered upstream to news mentioning the
    ticker, so we skip the local keyword filter via accept_all_sources). This is
    an explicit fallback, never the NG-curated feed — a non-energy asset never
    presents NG/energy-keyworded news as if it were its own.

    Yahoo's per-symbol feed URL format:
        https://feeds.finance.yahoo.com/rss/2.0/headline?s=<SYMBOL>=F&region=US&lang=en-US

    Works for any of our 26 instruments since they all have a valid =F
    continuous ticker (verified during the watchlist expansion).
    """
    upper = symbol.upper()
    source_id = f"yahoo_finance_{upper.lower()}"
    return SymbolNewsConfig(
        feeds={
            source_id: (
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={upper}=F&region=US&lang=en-US",
                "rss",
            ),
        },
        keywords=[],
        accept_all_sources=frozenset({source_id}),
    )


# ── Categorization (shared) ───────────────────────────────────────────────

# Soft category classifier — first keyword match wins. Order matters.
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("storage", ["storage", "inventory", "working gas", "bcf injection", "bcf withdrawal", "cushing"]),
    ("weather", ["cold snap", "heat dome", "polar vortex", "hdd", "cdd", "temperature anomaly"]),
    ("lng_export", ["lng export", "feedgas", "lng cargo", "ferc", "lng terminal"]),
    ("production", ["production", "well", "rig count", "frac", "haynesville", "appalachian", "permian", "drilling"]),
    ("refining", ["refinery", "refining", "distillate", "gasoline crack"]),
    # Monetary / macro — drivers for metals (gold, silver). Listed before
    # regulatory so a Fed/FOMC headline doesn't get caught by "policy".
    ("monetary", ["fomc", "fed", "rate cut", "rate hike", "real yields", "dollar", "dxy", "safe haven", "central bank"]),
    ("regulatory", ["epa", "ferc", "regulation", "policy", "tax", "spr"]),
    ("geopolitical", ["russia", "europe gas", "ukraine", "sanction", "import", "opec", "iran"]),
]

_CACHE_TTL_SECONDS = 10 * 60
_TAG_RE = re.compile(r"<[^>]+>")


def _classify(text: str) -> str:
    lower = text.lower()
    for category, needles in _CATEGORY_RULES:
        for needle in needles:
            if needle in lower:
                return category
    return "other"


def _strip_tags(html: str) -> str:
    return _TAG_RE.sub("", html).strip()


def _parse_pub_date(raw: str | None) -> str | None:
    """Accepts RFC 822 (RSS) or ISO 8601 (Atom)."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _parse_rss(xml_bytes: bytes, source_id: str) -> list[dict[str, Any]]:
    """Parse RSS 2.0 → list of normalized item dicts (pre-filter)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("RSS parse error for source=%s: %s", source_id, exc)
        return []
    items: list[dict[str, Any]] = []
    for el in root.iter("item"):
        title = (el.findtext("title") or "").strip()
        link = (el.findtext("link") or "").strip()
        pub_date_raw = el.findtext("pubDate")
        description = _strip_tags(el.findtext("description") or "")
        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date_raw,
                "source_id": source_id,
            }
        )
    return items


def _parse_atom(xml_bytes: bytes, source_id: str) -> list[dict[str, Any]]:
    """Parse Atom 1.0 → same normalized item dicts as _parse_rss."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("Atom parse error for source=%s: %s", source_id, exc)
        return []
    items: list[dict[str, Any]] = []
    for el in root.iter(f"{_ATOM_NS}entry"):
        title = (el.findtext(f"{_ATOM_NS}title") or "").strip()
        link_el = el.find(f"{_ATOM_NS}link")
        link = link_el.get("href", "") if link_el is not None else ""
        published = el.findtext(f"{_ATOM_NS}published") or el.findtext(
            f"{_ATOM_NS}updated"
        )
        summary = _strip_tags(el.findtext(f"{_ATOM_NS}summary") or "")
        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "description": summary,
                "pubDate": published,
                "source_id": source_id,
            }
        )
    return items


def _parse_feed(xml_bytes: bytes, source_id: str, fmt: str) -> list[dict[str, Any]]:
    if fmt == "atom":
        return _parse_atom(xml_bytes, source_id)
    return _parse_rss(xml_bytes, source_id)


def _to_event(
    item: dict[str, Any], default_category: str | None = None
) -> dict[str, Any] | None:
    """Normalize a parsed RSS/Atom item into the news_event dict shape.

    Legacy callers (and tests) invoke this without a default_category; in
    that mode the classifier runs against the title+description. New
    per-symbol callers may pass an override from
    SymbolNewsConfig.default_categories (e.g. NWS alerts always classify as
    "weather" regardless of body text).
    """
    published = _parse_pub_date(item.get("pubDate"))
    if published is None:
        return None
    if default_category is None:
        # Pre-Phase-14 behavior: check the legacy NG default_categories map
        # so existing callers' expectations for source-id overrides keep
        # working (e.g. nws_alerts → "weather").
        default_category = _NG_CONFIG.default_categories.get(
            item.get("source_id", "")
        )
    if default_category is not None:
        category = default_category
    else:
        category = _classify(
            f"{item.get('title', '')} {item.get('description', '')}"
        )
    return {
        "published_at": published,
        "source": item.get("source_id", ""),
        "headline": item["title"],
        "body": item.get("description") or "",
        "category": category,
        # We don't have an LLM-derived impact score at the adapter layer.
        "impact_score": 0.5,
        "affected_regions": [],
        "entities": [],
        "url": item.get("link") or None,
    }


# ── Adapter ──────────────────────────────────────────────────────────────


class RssNewsAdapter:
    """Per-instrument NewsDataAdapter reading curated RSS feeds.

    Construct one instance per symbol so the 10-min response cache and the
    keyword filter stay consistent. Curated configs exist for NG/CL/HO/RB/GC/SI;
    any other symbol falls through to a generic Yahoo per-symbol feed
    (_make_default_config) rather than 500-ing the news endpoint.
    """

    def __init__(self, symbol: str = "NG") -> None:
        upper = (symbol or "NG").upper()
        self._symbol = upper
        self._config = SYMBOL_CONFIGS.get(upper) or _make_default_config(upper)
        self._client = AdapterHTTPClient(
            adapter_name=f"news.rss.{upper.lower()}"
        )
        self._cache: tuple[float, list[dict[str, Any]]] | None = None

    async def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        events = await self._get_events_cached()
        return events[:limit]

    async def get_events_by_category(
        self, category: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        events = await self._get_events_cached()
        return [e for e in events if e.get("category") == category][:limit]

    def _matches_keywords(self, item: dict[str, str]) -> bool:
        haystack = f"{item.get('title', '')} {item.get('description', '')}".lower()
        return any(k in haystack for k in self._config.keywords)

    def _should_keep(self, item: dict[str, str]) -> bool:
        if item.get("source_id") in self._config.accept_all_sources:
            return True
        return self._matches_keywords(item)

    async def _get_events_cached(self) -> list[dict[str, Any]]:
        now = time.time()
        if self._cache is not None:
            cached_at, cached_data = self._cache
            if now - cached_at < _CACHE_TTL_SECONDS:
                return cached_data
        events = await self._fetch_all()
        self._cache = (now, events)
        return events

    async def _fetch_all(self) -> list[dict[str, Any]]:
        sources = list(self._config.feeds.items())
        results = await asyncio.gather(
            *(self._fetch_one(name, url, fmt) for name, (url, fmt) in sources),
            return_exceptions=False,
        )

        merged: list[dict[str, Any]] = []
        for (source_id, _spec), items in zip(sources, results):
            kept: list[dict[str, Any]] = []
            for item in items:
                if not self._should_keep(item):
                    continue
                event = _to_event(
                    item, self._config.default_categories.get(source_id)
                )
                if event is None:
                    continue
                kept.append(event)
            cap = self._config.source_caps.get(source_id)
            if cap is not None:
                kept.sort(key=lambda e: e["published_at"], reverse=True)
                kept = kept[:cap]
            merged.extend(kept)

        # Dedupe by headline+source; sort newest first.
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for e in merged:
            key = (e["headline"], e["source"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(e)

        deduped.sort(key=lambda e: e["published_at"], reverse=True)
        return deduped

    async def _fetch_one(
        self, source_id: str, url: str, fmt: str
    ) -> list[dict[str, Any]]:
        try:
            response = await self._client.get(
                url,
                headers={
                    "User-Agent": "Goldeneye-research-terminal/0.1 (+contact@example.com)"
                },
            )
        except Exception as exc:
            logger.warning("Feed fetch failed for source=%s: %s", source_id, exc)
            return []
        return _parse_feed(response.content, source_id, fmt)


# ── Backwards-compat module-level exports for pre-Phase-14 callers ────────

FEEDS = _NG_CONFIG.feeds
NG_KEYWORDS = _NG_CONFIG.keywords


def _matches_ng(item: dict[str, str]) -> bool:
    """Legacy NG keyword check. New code should use a per-symbol adapter."""
    haystack = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return any(k in haystack for k in NG_KEYWORDS)


def _should_keep(item: dict[str, str]) -> bool:
    """Legacy per-source filter for NG. New code should use the adapter's
    instance method which honors the per-symbol config."""
    if item.get("source_id") in _NG_CONFIG.accept_all_sources:
        return True
    return _matches_ng(item)
