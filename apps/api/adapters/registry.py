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
    - CL / HO / RB → EIA petroleum weekly stocks (per-symbol series table)
    - Everything else (metals, grains, …) → NullEnergyAdapter (empty), so a
      non-energy instrument never gets bogus gas-storage alt-data and never 500s.

    The Null routing applies in both mock and real modes — a metal has no EIA
    inventory report regardless of adapter configuration.
    """
    from apps.api.adapters.energy.eia_petroleum import PETROLEUM_SERIES

    upper = symbol.upper() if symbol else "NG"
    if upper != "NG" and upper not in PETROLEUM_SERIES:
        from apps.api.adapters.energy.null_energy import NullEnergyAdapter
        return NullEnergyAdapter()
    if settings.adapter_energy == "mock" or not settings.eia_api_key:
        from apps.api.adapters.energy.mock_eia import MockEIAAdapter
        return MockEIAAdapter()
    if upper in PETROLEUM_SERIES:
        from apps.api.adapters.energy.eia_petroleum import EIAPetroleumAdapter
        return EIAPetroleumAdapter(upper)
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
def get_news(symbol: str = "NG"):
    """Return the news adapter for the given instrument.

    RSS adapter spins up per-symbol instances so the per-instrument feeds
    + keyword filter are honored (NG keywords + NWS alerts vs CL keywords
    + OilPrice). Mock and NewsAPI fall through symbol-agnostic.
    """
    upper = symbol.upper() if symbol else "NG"
    if settings.adapter_news == "rss":
        from apps.api.adapters.news.rss import RssNewsAdapter
        return RssNewsAdapter(upper)
    if settings.adapter_news == "mock":
        from apps.api.adapters.news.mock_news import MockNewsAdapter
        return MockNewsAdapter()
    from apps.api.adapters.news.newsapi import NewsAPIAdapter
    return NewsAPIAdapter()
