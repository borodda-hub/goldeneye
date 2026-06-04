"""Phase 17 — per-symbol news configs for the thin-tier quartet + monetary rule.

Tests the keyword-filter and category classifier directly (no network).
"""
from __future__ import annotations

from apps.api.adapters.news.rss import (
    SYMBOL_CONFIGS,
    RssNewsAdapter,
    _classify,
)


def test_curated_configs_for_all_six_symbols():
    assert set(SYMBOL_CONFIGS) >= {"NG", "CL", "HO", "RB", "GC", "SI"}


def test_gc_filter_rejects_natural_gas_headline():
    gc = RssNewsAdapter("GC")
    ng_headline = {
        "title": "EIA natural gas storage rises on mild weather",
        "description": "Henry Hub natgas inventory build",
        "source_id": "kitco_news",  # not an accept-all source for GC
    }
    assert gc._should_keep(ng_headline) is False


def test_gc_filter_keeps_gold_headline():
    gc = RssNewsAdapter("GC")
    gold_headline = {
        "title": "Gold climbs as Fed signals a rate cut",
        "description": "Bullion gains on safe haven demand",
        "source_id": "kitco_news",
    }
    assert gc._should_keep(gold_headline) is True


def test_yahoo_per_symbol_source_is_accept_all():
    """The symbol's own Yahoo feed is pre-filtered by ticker → keyword-free."""
    si = RssNewsAdapter("SI")
    off_topic = {
        "title": "Completely unrelated market chatter",
        "description": "",
        "source_id": "yahoo_finance_si",
    }
    assert si._should_keep(off_topic) is True


def test_monetary_category_classifies_fed_headline():
    assert _classify("Gold rises after FOMC signals a rate cut") == "monetary"
    assert _classify("Silver dips as real yields climb") == "monetary"
    assert _classify("The Fed's next move will determine gold's direction") == "monetary"
    assert _classify("Gold climbs as the dollar weakens") == "monetary"


def test_monetary_does_not_override_energy_categories():
    """Production/lng/refining rules precede monetary, so energy headlines
    mentioning the Fed still classify as energy."""
    assert _classify("Permian drilling slows even as the Fed holds rates") == "production"


def test_storage_still_classifies_for_gas():
    assert _classify("EIA reports a large working gas storage injection") == "storage"


def test_metals_configs_include_kitco_feed():
    for sym in ("GC", "SI"):
        assert "kitco_news" in SYMBOL_CONFIGS[sym].feeds
