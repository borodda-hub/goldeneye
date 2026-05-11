"""Unit tests for the four generators. No DB needed — just call generate() and check shape."""
import pytest
from datetime import datetime, date
from apps.api.seeds.price_generator import generate as gen_prices
from apps.api.seeds.storage_generator import generate as gen_storage
from apps.api.seeds.cot_generator import generate as gen_cot
from apps.api.seeds.weather_generator import generate as gen_weather


def test_price_generator_daily_count():
    result = gen_prices()
    daily = [b for b in result["bars"] if b["resolution"] == "1d"]
    assert 720 <= len(daily) <= 740, f"Expected ~730 daily bars, got {len(daily)}"


def test_price_generator_ohlc_invariants():
    result = gen_prices()
    for bar in result["bars"][:200]:  # sample first 200
        assert bar["high"] >= bar["open"], f"high < open: {bar}"
        assert bar["high"] >= bar["close"], f"high < close: {bar}"
        assert bar["low"] <= bar["open"], f"low > open: {bar}"
        assert bar["low"] <= bar["close"], f"low > close: {bar}"
        assert bar["high"] >= bar["low"], f"high < low: {bar}"


def test_price_generator_minute_bars():
    result = gen_prices()
    minute = [b for b in result["bars"] if b["resolution"] == "1m"]
    assert len(minute) >= 14 * 390, f"Expected >= 5460 1-min bars, got {len(minute)}"


def test_price_generator_curve_snapshots():
    result = gen_prices()
    assert len(result["snapshots"]) >= 700
    first = result["snapshots"][0]
    assert len(first["curve"]) == 12


def test_storage_generator_count():
    rows = gen_storage()
    assert len(rows) == 100


def test_storage_generator_region_sums():
    rows = gen_storage()
    for row in rows:
        region_sum = (
            row["east_bcf"] + row["midwest_bcf"] + row["mountain_bcf"] +
            row["pacific_bcf"] + row["south_central_bcf"]
        )
        assert abs(region_sum - row["total_lower_48_bcf"]) < 1.0, \
            f"Region sum {region_sum} != total {row['total_lower_48_bcf']}"


def test_cot_generator_count():
    rows = gen_cot()
    assert len(rows) == 100


def test_cot_generator_nonnegative():
    rows = gen_cot()
    position_cols = [
        "producer_long", "producer_short", "swap_long", "swap_short",
        "managed_money_long", "managed_money_short",
        "other_reportable_long", "other_reportable_short",
        "nonreportable_long", "nonreportable_short",
    ]
    for row in rows:
        for col in position_cols:
            assert row[col] >= 0, f"{col} is negative in row {row['report_date']}"


def test_weather_generator_observation_count():
    result = gen_weather()
    obs = result["observations"]
    assert len(obs) == 60 * 6  # 60 days * 6 regions


def test_weather_generator_forecast_horizons():
    result = gen_weather()
    forecasts = result["forecasts"]
    for region in ["northeast", "midwest", "mountain", "pacific", "south_central", "southeast"]:
        region_forecasts = [f for f in forecasts if f["region"] == region]
        horizons = {f["horizon_days"] for f in region_forecasts}
        assert set(range(1, 15)) == horizons, f"Missing horizons for {region}: {horizons}"
