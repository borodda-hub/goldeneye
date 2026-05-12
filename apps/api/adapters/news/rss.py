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

FEEDS: dict[str, str] = {
    "eia_today_in_energy": "https://www.eia.gov/todayinenergy/rss.xml",
    "yahoo_finance_ng": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NG=F&region=US&lang=en-US",
}

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


def _parse_pub_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


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


def _to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    published = _parse_pub_date(item.get("pubDate"))
    if published is None:
        return None
    classified = _classify(f"{item.get('title', '')} {item.get('description', '')}")
    return {
        "published_at": published,
        "source": item["source_id"],
        "headline": item["title"],
        "body": item.get("description") or "",
        "category": classified,
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
        """Pull every configured feed in parallel, merge, filter, dedupe, sort."""
        results = await asyncio.gather(
            *(self._fetch_one(name, url) for name, url in FEEDS.items()),
            return_exceptions=False,
        )

        merged: list[dict[str, Any]] = []
        for items in results:
            for item in items:
                if not _matches_ng(item):
                    continue
                event = _to_event(item)
                if event is None:
                    continue
                merged.append(event)

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

    async def _fetch_one(self, source_id: str, url: str) -> list[dict[str, Any]]:
        try:
            response = await self._client.get(
                url,
                headers={"User-Agent": "NGTI-research-terminal/0.1 (+contact@example.com)"},
            )
        except Exception as exc:
            logger.warning("RSS fetch failed for source=%s: %s", source_id, exc)
            return []
        return _parse_rss(response.content, source_id)
