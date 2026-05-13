"""
Adapter registry. Returns the configured adapter instance for each domain.
Selection based on settings.adapter_* env vars.

Phase 14: energy and positioning adapters take a symbol argument so the
right per-instrument source is returned (EIA natural-gas storage for NG,
EIA petroleum stocks for CL; CFTC market code 023651 for NG, 067651 for CL).
Cached per-symbol via @lru_cache.

Usage:
    from apps.api.adapters.registry import get_market, get_energy, get_weather, get_positioning, get_news
    market = get_market()         # symbol-agnostic
    energy = get_energy("CL")     # EIA petroleum (Cushing)
    positioning = get_positioning("CL")  # CFTC WTI Crude (067651)
"""
from functools import lru_cache
from apps.api.src.settings import settings

@lru_cache(maxsize=None)
def get_market():
    if settings.adapter_market == "yahoo_delayed":
        from apps.api.adapters.market.yahoo_delayed import YahooDelayedMarketAdapter
        return YahooDelayedMarketAdapter()
    if settings.adapter_market == "mock":
        from apps.api.adapters.market.mock import MockMarketAdapter
        return MockMarketAdapter()
    from apps.api.adapters.market.nasdaq import NasdaqMarketAdapter
    return NasdaqMarketAdapter()


@lru_cache(maxsize=None)
def get_energy(symbol: str = "NG"):
    """Return the energy-storage adapter for the given instrument.

    - NG → EIA natural-gas weekly storage (Lower-48 + regional breakdowns)
    - CL → EIA petroleum weekly stocks (Cushing OK + total ex-SPR)
    - Unknown symbols silently fall back to mock NG storage so the
      dashboard never crashes on a freshly-added instrument.
    """
    upper = symbol.upper() if symbol else "NG"
    if settings.adapter_energy == "mock" or not settings.eia_api_key:
        from apps.api.adapters.energy.mock_eia import MockEIAAdapter
        return MockEIAAdapter()
    if upper == "CL":
        from apps.api.adapters.energy.eia_petroleum import EIAPetroleumAdapter
        return EIAPetroleumAdapter()
    from apps.api.adapters.energy.eia import EIAAdapter
    return EIAAdapter()


@lru_cache(maxsize=None)
def get_weather():
    if settings.adapter_weather == "mock":
        from apps.api.adapters.weather.mock_nws import MockNWSAdapter
        return MockNWSAdapter()
    from apps.api.adapters.weather.nws import NWSAdapter
    return NWSAdapter()


@lru_cache(maxsize=None)
def get_positioning(symbol: str = "NG"):
    """Return the COT positioning adapter for the given instrument.

    Real CFTC paths spin up a per-symbol instance (each holds its own 24h
    response cache). Mock path is symbol-agnostic.
    """
    if settings.adapter_positioning == "mock":
        from apps.api.adapters.positioning.mock_cftc import MockCFTCAdapter
        return MockCFTCAdapter()
    from apps.api.adapters.positioning.cftc import CFTCAdapter
    return CFTCAdapter(symbol.upper() if symbol else "NG")


@lru_cache(maxsize=None)
def get_news():
    if settings.adapter_news == "rss":
        from apps.api.adapters.news.rss import RssNewsAdapter
        return RssNewsAdapter()
    if settings.adapter_news == "mock":
        from apps.api.adapters.news.mock_news import MockNewsAdapter
        return MockNewsAdapter()
    from apps.api.adapters.news.newsapi import NewsAPIAdapter
    return NewsAPIAdapter()
