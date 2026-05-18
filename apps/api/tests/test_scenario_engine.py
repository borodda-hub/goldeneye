"""
Engine behavior tests for apps.api.services.scenario_engine.

Covers:
- `apply()` composability for weather/lng_export/production/storage shocks.
- `run_scenario` end-to-end for all 6 templates in packages/fixtures/scenario_templates.json.
- LLM call is mocked via monkeypatch on apps.api.services.scenario_engine.narrate_scenario.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.api.services import scenario_engine
from apps.api.services.model_registry import ForecastContext
from apps.api.services.safety import SafetyEnvelope
from apps.api.services.scenario_engine import apply, run_scenario


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def baseline_ctx() -> ForecastContext:
    """Baseline forecast context: 80 closes from 3.0 stepping up by 0.01."""
    return ForecastContext(
        symbol="NG",
        closes=[3.0 + 0.01 * i for i in range(80)],
        weather_anomaly=0.0,
        latest_storage={"delta": 0.0},
    )


@pytest.fixture
def stub_narrative() -> str:
    return (
        "Stub narrative text. This appears to suggest a directional pressure with a "
        "counterargument that needs validation. The scenario assumes the inputs hold for "
        "the stated days. Data that would validate or invalidate includes the next EIA "
        "storage report."
    )


@pytest.fixture(autouse=True)
def mock_narrate_scenario(monkeypatch: pytest.MonkeyPatch, stub_narrative: str) -> None:
    """Mock the LLM call so tests don't hit a live model."""

    async def _fake_narrate(scenario: dict, results: dict, ctx: dict) -> tuple[str, SafetyEnvelope]:
        envelope = SafetyEnvelope(
            confidence="medium",
            caveats=["test"],
            as_of=datetime.now(UTC),
        )
        return stub_narrative, envelope

    monkeypatch.setattr(scenario_engine, "narrate_scenario", _fake_narrate)


@pytest.fixture
def templates() -> list[dict]:
    fixtures_path = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "fixtures"
        / "scenario_templates.json"
    )
    return json.loads(fixtures_path.read_text())


# ---------------------------------------------------------------------------
# apply() unit tests
# ---------------------------------------------------------------------------
def test_apply_weather_shock_updates_weather_anomaly(baseline_ctx: ForecastContext) -> None:
    shocks = [
        {"type": "weather", "region": "northeast", "delta_temp_f": -12.0, "days": 10},
    ]
    shocked, assumptions, max_days = apply(shocks, baseline_ctx)

    assert shocked.weather_anomaly == pytest.approx(-12.0)
    assert max_days == 10
    assert len(assumptions) == 1
    assert "northeast" in assumptions[0]
    assert "-12" in assumptions[0]


def test_apply_composes_weather_and_lng_export(baseline_ctx: ForecastContext) -> None:
    """Weather and LNG-export shocks both push closes (weather: cold = up,
    LNG: more exports = up)."""
    shocks = [
        {"type": "weather", "region": "midwest", "delta_temp_f": -8.0, "days": 7},
        {"type": "lng_export", "delta_bcfd": 2.0, "days": 14},
    ]
    shocked, assumptions, max_days = apply(shocks, baseline_ctx)

    # Weather anomaly composed onto its own field.
    assert shocked.weather_anomaly == pytest.approx(-8.0)
    # Composed price impacts (days_factor 7d→1.0, 14d→2.0):
    #   weather: -8 °F × -0.005 × (7/7)  = +0.040
    #   lng:     +2 Bcf/d × 0.01 × (14/7) = +0.040
    #   total adjustment:                  +0.080
    expected_first_close = baseline_ctx.closes[0] + 0.08
    assert shocked.closes[0] == pytest.approx(expected_first_close, abs=1e-9)
    assert len(shocked.closes) == len(baseline_ctx.closes)
    assert len(assumptions) == 2
    assert max_days == 14


def test_apply_production_reduces_closes(baseline_ctx: ForecastContext) -> None:
    shocks = [{"type": "production", "delta_bcfd": 5.0, "days": 7}]
    shocked, assumptions, max_days = apply(shocks, baseline_ctx)

    # Production *increase* of +5 bcfd × -0.01 × (7d/7) = -0.05/MMBtu off every close.
    assert len(shocked.closes) == len(baseline_ctx.closes)
    for orig, new in zip(baseline_ctx.closes, shocked.closes):
        assert new == pytest.approx(orig - 0.05, abs=1e-9)
    assert len(assumptions) == 1


def test_apply_storage_shock_updates_latest_storage(baseline_ctx: ForecastContext) -> None:
    shocks = [{"type": "storage", "delta_bcf": -45.0, "days": 7}]
    shocked, assumptions, max_days = apply(shocks, baseline_ctx)

    # Storage shocks write delta_vs_consensus — that's the key xgboost actually
    # reads. Negative = smaller build / larger draw vs consensus = bullish.
    assert shocked.latest_storage is not None
    assert shocked.latest_storage["delta_vs_consensus"] == pytest.approx(-45.0)
    # Also nudges closes via heuristic: -45 × -0.0005 × 1.0 = +0.0225.
    assert shocked.closes[0] == pytest.approx(baseline_ctx.closes[0] + 0.0225, abs=1e-9)
    assert len(assumptions) == 1


def test_apply_composes_two_weather_shocks(baseline_ctx: ForecastContext) -> None:
    """Two weather shocks should accumulate on the anomaly."""
    shocks = [
        {"type": "weather", "region": "northeast", "delta_temp_f": -12.0, "days": 10},
        {"type": "weather", "region": "midwest", "delta_temp_f": -6.0, "days": 7},
    ]
    shocked, assumptions, max_days = apply(shocks, baseline_ctx)

    assert shocked.weather_anomaly == pytest.approx(-18.0)
    assert max_days == 10
    assert len(assumptions) == 2


def test_apply_returns_empty_assumptions_for_empty_shocks(baseline_ctx: ForecastContext) -> None:
    shocked, assumptions, max_days = apply([], baseline_ctx)

    assert shocked.closes == baseline_ctx.closes
    assert assumptions == []
    assert max_days == 0


# ---------------------------------------------------------------------------
# run_scenario integration over all 6 templates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_all_templates_run_to_completion(
    templates: list[dict],
    baseline_ctx: ForecastContext,
) -> None:
    assert len(templates) == 6, "Expected 6 scenario templates in the fixture file."

    for template in templates:
        result = await run_scenario(
            name=template["name"],
            instrument=template.get("instrument", "NG"),
            shocks=template["shocks"],
            baseline_ctx=baseline_ctx,
        )

        # Structural fields are deterministic, not LLM-generated.
        assert result["assumptions"], f"{template['id']}: empty assumptions"
        assert result["counterarguments"], f"{template['id']}: empty counterarguments"
        assert result["data_needed_to_validate"], f"{template['id']}: empty data_needed"
        assert result["narrative"], f"{template['id']}: empty narrative"

        assert result["directional_pressure"] in {"bullish", "bearish", "neutral"}, (
            f"{template['id']}: bad directional_pressure {result['directional_pressure']!r}"
        )
        assert result["confidence"] in {"low", "medium", "high"}, (
            f"{template['id']}: bad confidence {result['confidence']!r}"
        )
        assert "affected_timeframe" in result
        assert "expected_pct_range" in result
        assert "low" in result["expected_pct_range"]
        assert "high" in result["expected_pct_range"]
        assert "safety" in result


@pytest.mark.asyncio
async def test_run_scenario_returns_safety_envelope(
    baseline_ctx: ForecastContext,
) -> None:
    result = await run_scenario(
        name="Single weather shock",
        instrument="NG",
        shocks=[
            {"type": "weather", "region": "northeast", "delta_temp_f": -10.0, "days": 7},
        ],
        baseline_ctx=baseline_ctx,
    )

    safety = result["safety"]
    assert "confidence" in safety
    assert "caveats" in safety
    assert "as_of" in safety
    assert "disclaimer" in safety


@pytest.mark.asyncio
async def test_run_scenario_picks_correct_timeframe_label(
    baseline_ctx: ForecastContext,
) -> None:
    """A 21-day shock should produce 'affected_timeframe' = '1 month'."""
    result = await run_scenario(
        name="3-week LNG outage",
        instrument="NG",
        shocks=[{"type": "lng_export", "delta_bcfd": -2.0, "days": 21}],
        baseline_ctx=baseline_ctx,
    )
    assert result["affected_timeframe"] == "1 month"
