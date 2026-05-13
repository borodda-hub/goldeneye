"""Real NewsDataAdapter — pulls NG-relevant headlines from public RSS feeds.

Sources (free, no auth):
  - EIA "Today in Energy"  — https://www.eia.gov/todayinenergy/rss.xml
  - Yahoo Finance NG=F      — https://feeds.finance.yahoo.com/rss/2.0/headline?s=NG=F

Items are filtered by the NG_KEYWORDS list (case-insensitive substring match
on title or description). Results carry an extra `url` field that the mock
adapter doesn't — consumers that don't read it ignore it.

No DB persistence. The adapter fetches RSS on demand, caches for 10 min,
and returns dicts in the same shape as MockNewsAdapter (`published_at`,
`headline`, `source`, `body`, `category`, `impact_score`, plus `url`).
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

# Feed registry: id → (url, format).
# format: "rss" → RSS 2.0 with <item> elements; "atom" → Atom with <entry>.
FEEDS: dict[str, tuple[str, str]] = {
    "eia_today_in_energy": (
        "https://www.eia.gov/todayinenergy/rss.xml",
        "rss",
    ),
    "yahoo_finance_ng": (
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NG=F&region=US&lang=en-US",
        "rss",
    ),
    # NWS active alerts across the major gas-demand states. Atom feed.
    # All alerts in these regions count as NG-relevant weather context — the
    # default keyword filter is too tight for NWS event titles, so we let
    # everything through for this source and tag it as `weather`.
    "nws_alerts": (
        "https://api.weather.gov/alerts/active.atom?area=TX,LA,PA,NY,OK,OH,MI,IL,PA",
        "atom",
    ),
}

# Sources for which the NG_KEYWORDS filter is too tight — accept every item
# they publish (they're already pre-filtered upstream — e.g. NWS region-scoped
# alerts are inherently in NG-demand territory).
_ACCEPT_ALL_SOURCES: frozenset[str] = frozenset({"nws_alerts"})

# Per-source default category override. None = run the keyword classifier.
_SOURCE_DEFAULT_CATEGORY: dict[str, str | None] = {
    "nws_alerts": "weather",
}

# Per-source cap on items contributed to the merged feed. NWS fires dozens
# of alerts a day during active weather; without a cap it floods out Yahoo
# and EIA. None = no cap.
_SOURCE_CAPS: dict[str, int | None] = {
    "nws_alerts": 5,
}

# Roadmap (not enabled — neither has a stable public RSS I can confirm):
#  - CME Group exchange notices / NG-specific advisories. CME publishes a
#    daily bulletin (HTML) and product-specific PDFs but no clean public
#    RSS that I can verify points at NG-relevant content. Adding when
#    available; for now the adapter just won't have CME items.
#  - NOAA Climate Prediction Center 6-10 day discussions. Text products,
#    not RSS. Would need a scraper.

NG_KEYWORDS: list[str] = [
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
]

# Soft category classifier — first keyword match wins. Order matters.
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("storage", ["storage", "inventory", "working gas", "bcf injection", "bcf withdrawal"]),
    ("weather", ["cold snap", "heat dome", "polar vortex", "hdd", "cdd", "temperature anomaly"]),
    ("lng_export", ["lng export", "feedgas", "lng cargo", "ferc", "lng terminal"]),
    ("production", ["production", "well", "rig count", "frac", "haynesville", "appalachian", "permian"]),
    ("regulatory", ["epa", "ferc", "regulation", "policy", "tax"]),
    ("geopolitical", ["russia", "europe gas", "ukraine", "sanction", "import"]),
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


def _matches_ng(item: dict[str, str]) -> bool:
    haystack = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return any(k in haystack for k in NG_KEYWORDS)


def _should_keep(item: dict[str, str]) -> bool:
    """Per-source filter — accept-all sources skip the NG keyword check."""
    if item.get("source_id") in _ACCEPT_ALL_SOURCES:
        return True
    return _matches_ng(item)


def _parse_pub_date(raw: str | None) -> str | None:
    """Accepts RFC 822 (RSS) or ISO 8601 (Atom)."""
    if not raw:
        return None
    raw = raw.strip()
    # RFC 822 first — that's what RSS produces.
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    # ISO 8601 fallback for Atom feeds.
    try:
        # fromisoformat handles "2026-05-11T20:30:00-04:00" since Python 3.11.
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
    """Parse Atom 1.0 (NWS alerts) → same normalized item dicts as _parse_rss."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("Atom parse error for source=%s: %s", source_id, exc)
        return []
    items: list[dict[str, Any]] = []
    for el in root.iter(f"{_ATOM_NS}entry"):
        title = (el.findtext(f"{_ATOM_NS}title") or "").strip()
        # Atom <link href="..."/>
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
                # Atom uses ISO8601 instead of RFC822; _parse_pub_date handles both.
                "pubDate": published,
                "source_id": source_id,
            }
        )
    return items


def _parse_feed(xml_bytes: bytes, source_id: str, fmt: str) -> list[dict[str, Any]]:
    if fmt == "atom":
        return _parse_atom(xml_bytes, source_id)
    return _parse_rss(xml_bytes, source_id)


def _to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    published = _parse_pub_date(item.get("pubDate"))
    if published is None:
        return None
    source_id = item.get("source_id", "")
    # Per-source category override (e.g., NWS alerts are always "weather").
    default = _SOURCE_DEFAULT_CATEGORY.get(source_id)
    if default is not None:
        category = default
    else:
        category = _classify(
            f"{item.get('title', '')} {item.get('description', '')}"
        )
    return {
        "published_at": published,
        "source": source_id,
        "headline": item["title"],
        "body": item.get("description") or "",
        "category": category,
        # We don't have an LLM-derived impact score at the adapter layer.
        # 0.5 is a neutral default; consumers that need real scoring should
        # call services.llm_explainer.extract_event on the body.
        "impact_score": 0.5,
        "affected_regions": [],
        "entities": [],
        "url": item.get("link") or None,
    }


class RssNewsAdapter:
    """Real NewsDataAdapter implementation reading curated RSS feeds."""

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="news.rss")
        self._cache: tuple[float, list[dict[str, Any]]] | None = None

    async def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        events = await self._get_events_cached()
        return events[:limit]

    async def get_events_by_category(self, category: str, limit: int = 10) -> list[dict[str, Any]]:
        events = await self._get_events_cached()
        return [e for e in events if e.get("category") == category][:limit]

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
        """Pull every configured feed in parallel, merge, filter, dedupe, sort.

        Per-source caps applied before merging so one chatty source (e.g. NWS
        during active weather) can't drown out the others.
        """
        sources = list(FEEDS.items())
        results = await asyncio.gather(
            *(self._fetch_one(name, url, fmt) for name, (url, fmt) in sources),
            return_exceptions=False,
        )

        merged: list[dict[str, Any]] = []
        for (source_id, _spec), items in zip(sources, results):
            kept: list[dict[str, Any]] = []
            for item in items:
                if not _should_keep(item):
                    continue
                event = _to_event(item)
                if event is None:
                    continue
                kept.append(event)
            cap = _SOURCE_CAPS.get(source_id)
            if cap is not None:
                # Newest-first within the source so the cap keeps the freshest.
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
                headers={"User-Agent": "Goldeneye-research-terminal/0.1 (+contact@example.com)"},
            )
        except Exception as exc:
            logger.warning("Feed fetch failed for source=%s: %s", source_id, exc)
            return []
        return _parse_feed(response.content, source_id, fmt)
