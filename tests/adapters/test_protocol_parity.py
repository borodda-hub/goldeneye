"""
For each domain, verify mock and real adapters expose the same public methods.
"""
import pytest
from apps.api.adapters.base import MarketDataAdapter, EnergyDataAdapter, WeatherDataAdapter, PositioningDataAdapter, NewsDataAdapter
from apps.api.adapters.market.mock import MockMarketAdapter
from apps.api.adapters.market.nasdaq import NasdaqMarketAdapter
from apps.api.adapters.energy.mock_eia import MockEIAAdapter
from apps.api.adapters.energy.eia import EIAAdapter
from apps.api.adapters.weather.mock_nws import MockNWSAdapter
from apps.api.adapters.weather.nws import NWSAdapter
from apps.api.adapters.positioning.mock_cftc import MockCFTCAdapter
from apps.api.adapters.positioning.cftc import CFTCAdapter
from apps.api.adapters.news.mock_news import MockNewsAdapter
from apps.api.adapters.news.newsapi import NewsAPIAdapter

def _public_methods(cls) -> set[str]:
    return {m for m in dir(cls) if not m.startswith("_") and callable(getattr(cls, m))}

@pytest.mark.parametrize("mock_cls,real_cls", [
    (MockMarketAdapter, NasdaqMarketAdapter),
    (MockEIAAdapter, EIAAdapter),
    (MockNWSAdapter, NWSAdapter),
    (MockCFTCAdapter, CFTCAdapter),
    (MockNewsAdapter, NewsAPIAdapter),
])
def test_method_parity(mock_cls, real_cls):
    mock_methods = _public_methods(mock_cls)
    real_methods = _public_methods(real_cls)
    assert mock_methods == real_methods, (
        f"{mock_cls.__name__} vs {real_cls.__name__}: "
        f"mock has {mock_methods - real_methods}, real has {real_methods - mock_methods}"
    )

def test_mock_market_implements_protocol():
    assert isinstance(MockMarketAdapter(), MarketDataAdapter)

def test_mock_energy_implements_protocol():
    assert isinstance(MockEIAAdapter(), EnergyDataAdapter)

def test_mock_weather_implements_protocol():
    assert isinstance(MockNWSAdapter(), WeatherDataAdapter)

def test_mock_positioning_implements_protocol():
    assert isinstance(MockCFTCAdapter(), PositioningDataAdapter)

def test_mock_news_implements_protocol():
    assert isinstance(MockNewsAdapter(), NewsDataAdapter)
