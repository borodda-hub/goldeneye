"""
Adapter registry. Returns the configured adapter instance for each domain.
Selection based on settings.adapter_* env vars.

Usage:
    from apps.api.adapters.registry import get_market, get_energy, get_weather, get_positioning, get_news
    market = get_market()  # returns MockMarketAdapter or NasdaqMarketAdapter
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
def get_energy():
    # Silent fallback to mock when the real adapter is selected but EIA_API_KEY
    # is missing — keeps demo bootable on a fresh clone.
    if settings.adapter_energy == "mock" or not settings.eia_api_key:
        from apps.api.adapters.energy.mock_eia import MockEIAAdapter
        return MockEIAAdapter()
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
def get_positioning():
    if settings.adapter_positioning == "mock":
        from apps.api.adapters.positioning.mock_cftc import MockCFTCAdapter
        return MockCFTCAdapter()
    from apps.api.adapters.positioning.cftc import CFTCAdapter
    return CFTCAdapter()

@lru_cache(maxsize=None)
def get_news():
    if settings.adapter_news == "mock":
        from apps.api.adapters.news.mock_news import MockNewsAdapter
        return MockNewsAdapter()
    from apps.api.adapters.news.newsapi import NewsAPIAdapter
    return NewsAPIAdapter()
