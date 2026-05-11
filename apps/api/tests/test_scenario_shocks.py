"""
Pydantic validation tests for the strict shock discriminated union in
apps.api.routers.scenarios. See docs/PHASE_06_PLAN.md §override 2.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.api.routers.scenarios import (
    LngExportShock,
    ProductionShock,
    ScenarioRunRequest,
    StorageShock,
    WeatherShock,
)


# ---------------------------------------------------------------------------
# Accepts valid shocks of each type
# ---------------------------------------------------------------------------
def test_accepts_valid_weather_shock() -> None:
    shock = WeatherShock(type="weather", region="northeast", delta_temp_f=-12.0, days=10)
    assert shock.type == "weather"
    assert shock.region == "northeast"
    assert shock.delta_temp_f == -12.0
    assert shock.days == 10


def test_accepts_valid_lng_export_shock() -> None:
    shock = LngExportShock(type="lng_export", delta_bcfd=-2.1, days=14)
    assert shock.type == "lng_export"
    assert shock.delta_bcfd == -2.1
    assert shock.days == 14


def test_accepts_valid_production_shock() -> None:
    shock = ProductionShock(type="production", delta_bcfd=-3.5, days=7)
    assert shock.type == "production"
    assert shock.delta_bcfd == -3.5
    assert shock.days == 7


def test_accepts_valid_storage_shock() -> None:
    shock = StorageShock(type="storage", delta_bcf=-45.0, days=7)
    assert shock.type == "storage"
    assert shock.delta_bcf == -45.0
    assert shock.days == 7


# ---------------------------------------------------------------------------
# Rejects unknown shock type via the discriminator
# ---------------------------------------------------------------------------
def test_rejects_unknown_shock_type() -> None:
    with pytest.raises(ValidationError) as exc:
        ScenarioRunRequest.model_validate(
            {
                "instrument": "NG",
                "name": "Nuclear winter",
                "shocks": [{"type": "nuclear", "days": 5}],
            }
        )
    # Discriminator error should reference the bad tag
    assert "nuclear" in str(exc.value).lower() or "discriminat" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Rejects out-of-bounds deltas
# ---------------------------------------------------------------------------
def test_rejects_out_of_bounds_delta_temp_f_low() -> None:
    with pytest.raises(ValidationError):
        WeatherShock(type="weather", region="northeast", delta_temp_f=-100.0, days=10)


def test_rejects_out_of_bounds_delta_temp_f_high() -> None:
    with pytest.raises(ValidationError):
        WeatherShock(type="weather", region="northeast", delta_temp_f=75.0, days=10)


def test_rejects_out_of_bounds_delta_bcfd_lng_export() -> None:
    with pytest.raises(ValidationError):
        LngExportShock(type="lng_export", delta_bcfd=50.0, days=10)


def test_rejects_out_of_bounds_delta_bcfd_production() -> None:
    with pytest.raises(ValidationError):
        ProductionShock(type="production", delta_bcfd=-50.0, days=10)


def test_rejects_out_of_bounds_delta_bcf_storage() -> None:
    with pytest.raises(ValidationError):
        StorageShock(type="storage", delta_bcf=1000.0, days=10)


def test_rejects_out_of_bounds_days_low() -> None:
    with pytest.raises(ValidationError):
        WeatherShock(type="weather", region="northeast", delta_temp_f=-5.0, days=0)


def test_rejects_out_of_bounds_days_high() -> None:
    with pytest.raises(ValidationError):
        WeatherShock(type="weather", region="northeast", delta_temp_f=-5.0, days=120)


# ---------------------------------------------------------------------------
# Rejects empty/oversized shocks lists
# ---------------------------------------------------------------------------
def test_rejects_empty_shocks_list() -> None:
    with pytest.raises(ValidationError):
        ScenarioRunRequest(instrument="NG", name="Empty scenario", shocks=[])


def test_rejects_oversized_shocks_list() -> None:
    too_many = [
        WeatherShock(type="weather", region="northeast", delta_temp_f=-5.0, days=5)
        for _ in range(11)
    ]
    with pytest.raises(ValidationError):
        ScenarioRunRequest(instrument="NG", name="Too many shocks", shocks=too_many)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Rejects fields that don't belong to the chosen discriminator branch
# ---------------------------------------------------------------------------
def test_rejects_wrong_field_for_weather_type() -> None:
    """A weather shock with delta_bcfd (an lng_export/production field) must fail."""
    with pytest.raises(ValidationError):
        # WeatherShock requires region + delta_temp_f; missing them should raise.
        WeatherShock.model_validate(
            {"type": "weather", "delta_bcfd": 1.0, "days": 5}
        )


def test_rejects_wrong_field_for_lng_export_type() -> None:
    """An lng_export shock with delta_temp_f instead of delta_bcfd must fail."""
    with pytest.raises(ValidationError):
        LngExportShock.model_validate(
            {"type": "lng_export", "delta_temp_f": -5.0, "days": 5}
        )


def test_rejects_missing_required_region_in_weather() -> None:
    with pytest.raises(ValidationError):
        WeatherShock.model_validate({"type": "weather", "delta_temp_f": -5.0, "days": 5})


def test_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ScenarioRunRequest(
            instrument="NG",
            name="",
            shocks=[WeatherShock(type="weather", region="northeast", delta_temp_f=-5.0, days=5)],
        )


# ---------------------------------------------------------------------------
# Discriminated union dispatches to the right class
# ---------------------------------------------------------------------------
def test_discriminator_dispatches_to_correct_class() -> None:
    req = ScenarioRunRequest.model_validate(
        {
            "instrument": "NG",
            "name": "Mixed shocks",
            "shocks": [
                {"type": "weather", "region": "northeast", "delta_temp_f": -10.0, "days": 7},
                {"type": "lng_export", "delta_bcfd": -2.0, "days": 14},
                {"type": "production", "delta_bcfd": -3.0, "days": 7},
                {"type": "storage", "delta_bcf": -50.0, "days": 7},
            ],
        }
    )
    assert isinstance(req.shocks[0], WeatherShock)
    assert isinstance(req.shocks[1], LngExportShock)
    assert isinstance(req.shocks[2], ProductionShock)
    assert isinstance(req.shocks[3], StorageShock)
