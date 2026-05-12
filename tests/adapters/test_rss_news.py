"""Unit tests for the real RSS news adapter — parsing, NG filter, classification, cache."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.adapters.news.rss import (
    FEEDS,
    NG_KEYWORDS,
    RssNewsAdapter,
    _classify,
    _matches_ng,
    _parse_atom,
    _parse_pub_date,
    _parse_rss,
    _should_keep,
    _strip_tags,
    _to_event,
)


# ── helpers ───────────────────────────────────────────────────────────────


def _rss(items_xml: str, channel_title: str = "Test Feed") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{channel_title}</title>
    <link>https://example.com</link>
    {items_xml}
  </channel>
</rss>""".strip().encode()


def _item(
    title: str,
    link: str = "https://example.com/a",
    pub: str = "Mon, 12 May 2026 10:00:00 GMT",
    desc: str = "",
) -> str:
    return f"""<item>
  <title>{title}</title>
  <link>{link}</link>
  <pubDate>{pub}</pubDate>
  <description><![CDATA[{desc}]]></description>
</item>"""


# ── pure parsers ──────────────────────────────────────────────────────────


def test_strip_tags_removes_html():
    assert _strip_tags("<p>Hello <b>world</b></p>") == "Hello world"
    assert _strip_tags("no tags here") == "no tags here"
    assert _strip_tags("") == ""


def test_parse_pub_date_handles_rfc822():
    iso = _parse_pub_date("Mon, 12 May 2026 14:30:00 GMT")
    assert iso is not None and iso.startswith("2026-05-12T14:30:00")


def test_parse_pub_date_returns_none_on_garbage():
    assert _parse_pub_date(None) is None
    assert _parse_pub_date("not a date") is None
    assert _parse_pub_date("") is None


def test_parse_rss_extracts_items():
    xml = _rss(
        _item("Headline A", desc="natural gas update")
        + _item("Headline B", pub="Tue, 13 May 2026 09:00:00 GMT")
    )
    items = _parse_rss(xml, "test_source")
    assert len(items) == 2
    assert items[0]["title"] == "Headline A"
    assert items[0]["source_id"] == "test_source"


def test_parse_rss_skips_items_without_title():
    xml = _rss(
        """<item><link>https://x/y</link><pubDate>Mon, 12 May 2026 10:00:00 GMT</pubDate></item>"""
        + _item("Real headline")
    )
    items = _parse_rss(xml, "src")
    assert len(items) == 1
    assert items[0]["title"] == "Real headline"


def test_parse_rss_tolerates_malformed_xml():
    items = _parse_rss(b"not valid xml at all", "src")
    assert items == []


def test_classify_picks_first_matching_category():
    assert _classify("EIA storage report shows draw") == "storage"
    assert _classify("Cold snap hits the Northeast") == "weather"
    assert _classify("LNG export terminal feedgas") == "lng_export"
    assert _classify("Permian gas production rises") == "production"
    assert _classify("Random unrelated content") == "other"


def test_matches_ng_filters_to_relevant_items():
    assert _matches_ng({"title": "Natural gas surges", "description": ""}) is True
    assert _matches_ng({"title": "Henry Hub up 5%", "description": ""}) is True
    assert _matches_ng({"title": "Equity markets rally", "description": "stocks gain"}) is False
    # Match via description even when title is unrelated.
    assert _matches_ng({"title": "Weekly update", "description": "LNG cargoes rising"}) is True


def test_to_event_returns_normalized_shape():
    event = _to_event(
        {
            "title": "EIA storage report draws 50 Bcf",
            "link": "https://eia.gov/x",
            "description": "Working gas in storage dropped 50 Bcf this week",
            "pubDate": "Thu, 08 May 2026 14:30:00 GMT",
            "source_id": "eia_today_in_energy",
        }
    )
    assert event is not None
    assert event["headline"] == "EIA storage report draws 50 Bcf"
    assert event["url"] == "https://eia.gov/x"
    assert event["source"] == "eia_today_in_energy"
    assert event["category"] == "storage"
    assert event["published_at"].startswith("2026-05-08T14:30:00")
    assert "impact_score" in event


def test_to_event_returns_none_when_pub_date_unparseable():
    event = _to_event(
        {
            "title": "test",
            "link": "x",
            "description": "",
            "pubDate": "garbage",
            "source_id": "src",
        }
    )
    assert event is None


# ── adapter behavior ──────────────────────────────────────────────────────


def _mock_response(body: bytes) -> object:
    return type("R", (), {"content": body})()


def _empty_rss() -> bytes:
    return _rss("")


def _single_feed_mock(xml: bytes) -> AsyncMock:
    """Return `xml` for the first feed call, empty RSS for the rest.

    The adapter calls every feed in `FEEDS`. Returning the same XML on every
    call would double up the results. Tests that want a single, controlled
    set of items should use this so only one feed contributes.
    """
    responses = [_mock_response(xml)] + [
        _mock_response(_empty_rss()) for _ in range(max(0, len(FEEDS) - 1))
    ]
    return AsyncMock(side_effect=responses)


def test_adapter_filters_to_ng_keywords():
    """Items not mentioning NG keywords are dropped."""
    xml = _rss(
        _item("Natural gas prices surge", desc="strong demand")
        + _item("Tech stocks drop", desc="market rotation")
    )

    adapter = RssNewsAdapter()
    with patch.object(adapter._client, "get", new=AsyncMock(return_value=_mock_response(xml))):
        events = asyncio.run(adapter.get_recent_events())
    titles = [e["headline"] for e in events]
    assert "Natural gas prices surge" in titles
    assert "Tech stocks drop" not in titles


def test_adapter_sorts_newest_first():
    older = _item("Natural gas item one", pub="Mon, 05 May 2026 10:00:00 GMT")
    newer = _item("Natural gas item two", pub="Mon, 12 May 2026 10:00:00 GMT")
    xml = _rss(older + newer)

    adapter = RssNewsAdapter()
    with patch.object(adapter._client, "get", new=_single_feed_mock(xml)):
        events = asyncio.run(adapter.get_recent_events())
    assert len(events) == 2
    assert events[0]["headline"] == "Natural gas item two"
    assert events[1]["headline"] == "Natural gas item one"


def test_adapter_dedupes_identical_headlines_from_same_source():
    """Two items in the same feed with the same title shouldn't double up."""
    xml = _rss(
        _item("Natural gas headline")
        + _item("Natural gas headline")  # same title same pubDate
    )

    adapter = RssNewsAdapter()
    with patch.object(adapter._client, "get", new=_single_feed_mock(xml)):
        events = asyncio.run(adapter.get_recent_events())
    titles = [e["headline"] for e in events]
    assert titles.count("Natural gas headline") == 1


def test_adapter_respects_limit():
    items = "".join(
        _item(f"Natural gas item {i}", pub=f"Mon, 12 May 2026 {10 + i:02d}:00:00 GMT")
        for i in range(5)
    )
    xml = _rss(items)

    adapter = RssNewsAdapter()
    with patch.object(adapter._client, "get", new=_single_feed_mock(xml)):
        events = asyncio.run(adapter.get_recent_events(limit=3))
    assert len(events) == 3


def test_adapter_filters_by_category():
    items = (
        _item("Natural gas EIA storage report shows draw", desc="storage week")
        + _item("Cold snap natural gas demand spike", desc="weather hits Midcontinent")
    )
    xml = _rss(items)

    adapter = RssNewsAdapter()
    # Two separate mock instances so each adapter call hits a fresh side_effect chain.
    with patch.object(adapter._client, "get", new=_single_feed_mock(xml)):
        storage = asyncio.run(adapter.get_events_by_category("storage"))
    # Reset cache for the second call so the mock chain is reused cleanly.
    adapter._cache = None
    with patch.object(adapter._client, "get", new=_single_feed_mock(xml)):
        weather = asyncio.run(adapter.get_events_by_category("weather"))
    assert len(storage) == 1
    assert storage[0]["category"] == "storage"
    assert len(weather) == 1
    assert weather[0]["category"] == "weather"


def test_adapter_cache_avoids_second_fetch():
    xml = _rss(_item("Natural gas test"))
    adapter = RssNewsAdapter()
    mock_get = AsyncMock(return_value=_mock_response(xml))
    with patch.object(adapter._client, "get", new=mock_get):
        asyncio.run(adapter.get_recent_events())
        asyncio.run(adapter.get_recent_events())
    # Each get_recent_events triggers one fetch per feed; cache should kick in
    # on the second call, so total await count matches the number of feeds.
    assert mock_get.await_count == len(FEEDS)


def test_adapter_survives_feed_fetch_error():
    """One feed blowing up shouldn't take down the whole adapter."""
    xml = _rss(_item("Natural gas survives"))
    adapter = RssNewsAdapter()
    call_count = {"n": 0}

    async def flaky(url, **_kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("first feed exploded")
        return _mock_response(xml)

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=flaky)):
        events = asyncio.run(adapter.get_recent_events())
    # Second feed still produced its filter-matching item.
    assert any(e["headline"] == "Natural gas survives" for e in events)


def test_ng_keywords_list_is_lowercase():
    """Filter uses .lower(); the keyword list must already be lowercase."""
    for kw in NG_KEYWORDS:
        assert kw == kw.lower(), f"keyword has uppercase: {kw!r}"


# ── Atom / NWS support ────────────────────────────────────────────────────


def _atom(entries_xml: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <id>urn:test:feed</id>
  {entries_xml}
</feed>""".strip().encode()


def _entry(
    title: str,
    href: str = "https://example.com/x",
    published: str = "2026-05-11T20:30:00-04:00",
    summary: str = "",
) -> str:
    return f"""<entry>
  <title>{title}</title>
  <link href="{href}"/>
  <published>{published}</published>
  <summary>{summary}</summary>
  <id>urn:test:{title}</id>
</entry>"""


def test_parse_atom_extracts_entries():
    xml = _atom(
        _entry("Winter Storm Warning issued for Pennsylvania")
        + _entry("Freeze Watch for Texas", published="2026-05-12T08:00:00Z")
    )
    items = _parse_atom(xml, "nws_alerts")
    assert len(items) == 2
    assert items[0]["title"] == "Winter Storm Warning issued for Pennsylvania"
    assert items[0]["link"] == "https://example.com/x"
    assert items[0]["source_id"] == "nws_alerts"


def test_parse_atom_skips_entries_without_title():
    xml = _atom(
        """<entry><id>urn:notitle</id><published>2026-05-11T20:30:00Z</published></entry>"""
        + _entry("Real alert")
    )
    items = _parse_atom(xml, "nws_alerts")
    assert len(items) == 1
    assert items[0]["title"] == "Real alert"


def test_parse_atom_tolerates_malformed_xml():
    items = _parse_atom(b"<not valid", "src")
    assert items == []


def test_parse_pub_date_handles_iso8601_atom():
    iso = _parse_pub_date("2026-05-11T20:30:00-04:00")
    assert iso is not None and iso.startswith("2026-05-12T00:30:00")


def test_parse_pub_date_handles_z_suffix():
    iso = _parse_pub_date("2026-05-11T20:30:00Z")
    assert iso is not None and iso.startswith("2026-05-11T20:30:00")


def test_should_keep_accepts_all_for_nws():
    """NWS items are accepted regardless of NG keywords."""
    nws_item = {
        "title": "Severe Thunderstorm Warning",  # no NG keyword
        "description": "Hail and damaging winds expected",
        "source_id": "nws_alerts",
    }
    assert _should_keep(nws_item) is True


def test_should_keep_still_filters_yahoo():
    """Other sources still go through the NG keyword filter."""
    irrelevant = {
        "title": "Apple announces new iPhone",
        "description": "tech news",
        "source_id": "yahoo_finance_ng",
    }
    assert _should_keep(irrelevant) is False


def test_to_event_overrides_category_for_nws():
    event = _to_event(
        {
            "title": "Severe Thunderstorm Warning",
            "link": "https://api.weather.gov/x",
            "description": "Hail and damaging winds",
            "pubDate": "2026-05-11T20:30:00-04:00",
            "source_id": "nws_alerts",
        }
    )
    assert event is not None
    assert event["category"] == "weather"


def test_feeds_registry_uses_tuple_shape():
    """All registry entries are (url, format) tuples; format is rss or atom."""
    for source_id, value in FEEDS.items():
        assert isinstance(value, tuple) and len(value) == 2, source_id
        url, fmt = value
        assert isinstance(url, str) and url.startswith("https://"), source_id
        assert fmt in ("rss", "atom"), source_id
