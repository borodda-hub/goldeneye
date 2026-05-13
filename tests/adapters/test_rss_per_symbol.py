"""Phase 14 step 5 — per-symbol news adapter behavior."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.api.adapters.news.rss import (
    RssNewsAdapter,
    SYMBOL_CONFIGS,
)


def test_symbol_configs_carry_ng_and_cl():
    assert "NG" in SYMBOL_CONFIGS
    assert "CL" in SYMBOL_CONFIGS


def test_ng_keywords_include_natgas_terms():
    ng = SYMBOL_CONFIGS["NG"]
    assert "natural gas" in ng.keywords
    assert "lng" in ng.keywords
    assert "henry hub" in ng.keywords


def test_cl_keywords_include_crude_terms():
    cl = SYMBOL_CONFIGS["CL"]
    assert "crude oil" in cl.keywords
    assert "wti" in cl.keywords
    assert "opec" in cl.keywords
    assert "cushing" in cl.keywords


def test_cl_config_has_no_nws_alerts():
    """CL doesn't get the gas-demand-state weather feed."""
    cl = SYMBOL_CONFIGS["CL"]
    assert "nws_alerts" not in cl.feeds
    assert "oilprice_main" in cl.feeds


def test_ng_config_has_nws_alerts():
    ng = SYMBOL_CONFIGS["NG"]
    assert "nws_alerts" in ng.feeds


def test_ng_adapter_keeps_natural_gas_item():
    adapter = RssNewsAdapter("NG")
    assert adapter._should_keep(
        {"title": "Henry Hub gas rallies", "description": "", "source_id": "x"}
    ) is True


def test_ng_adapter_drops_crude_only_item():
    """A 'WTI crude breaks $80' headline must not appear on the NG feed."""
    adapter = RssNewsAdapter("NG")
    assert adapter._should_keep(
        {
            "title": "WTI crude breaks $80 on OPEC headlines",
            "description": "",
            "source_id": "x",
        }
    ) is False


def test_cl_adapter_keeps_crude_item():
    adapter = RssNewsAdapter("CL")
    assert adapter._should_keep(
        {
            "title": "WTI crude breaks $80 on OPEC headlines",
            "description": "",
            "source_id": "x",
        }
    ) is True


def test_cl_adapter_drops_pure_natgas_item():
    """A 'Henry Hub gas rallies' headline should not appear on the CL feed."""
    adapter = RssNewsAdapter("CL")
    assert adapter._should_keep(
        {"title": "Henry Hub gas rallies", "description": "", "source_id": "x"}
    ) is False


def test_cl_adapter_accepts_eia_petroleum_item():
    adapter = RssNewsAdapter("CL")
    assert adapter._should_keep(
        {
            "title": "Cushing crude inventories drop",
            "description": "",
            "source_id": "eia_today_in_energy",
        }
    ) is True


def test_unknown_symbol_falls_back_to_ng_config():
    adapter = RssNewsAdapter("XYZ")
    assert adapter._config is SYMBOL_CONFIGS["NG"]


def test_ng_adapter_accepts_all_nws_items_without_keyword_match():
    """NWS alerts source is in accept_all_sources for NG."""
    adapter = RssNewsAdapter("NG")
    assert adapter._should_keep(
        {
            "title": "Severe thunderstorm warning",
            "description": "",
            "source_id": "nws_alerts",
        }
    ) is True


def test_registry_get_news_returns_per_symbol_instance():
    from apps.api.adapters.registry import get_news

    get_news.cache_clear()
    with patch("apps.api.adapters.registry.settings") as mock_settings:
        mock_settings.adapter_news = "rss"
        ng_adapter = get_news("NG")
        cl_adapter = get_news("CL")
    assert isinstance(ng_adapter, RssNewsAdapter)
    assert isinstance(cl_adapter, RssNewsAdapter)
    assert ng_adapter._symbol == "NG"
    assert cl_adapter._symbol == "CL"
    # Separate instances → separate caches.
    assert ng_adapter is not cl_adapter
