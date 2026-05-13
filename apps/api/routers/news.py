"""News endpoints — adapter-direct, not DB-backed.

The Signal Lab UI calls /v1/news/recent to render a live feed below the
explanation panel. We bypass the news_events table here so the news stays
as fresh as the RSS feeds without needing a worker layer to persist.

The dashboard router still reads its "recent events" list from the
news_events DB table — that path is unchanged.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.adapters.registry import get_news

router = APIRouter(prefix="/v1/news", tags=["news"])


@router.get("/recent")
async def get_recent_news(
    symbol: str = Query(default="NG"),
    limit: int = Query(default=15, ge=1, le=100),
    category: str | None = Query(default=None),
) -> dict:
    """Return recent NG-relevant news items via the configured adapter.

    The mock adapter serves curated fixtures; the rss adapter pulls live
    items from EIA + Yahoo Finance and filters by NG keywords. Either way,
    the response shape is identical.
    """
    adapter = get_news(symbol)
    if category:
        events = await adapter.get_events_by_category(category, limit=limit)
    else:
        events = await adapter.get_recent_events(limit=limit)
    return {"events": events, "count": len(events)}
