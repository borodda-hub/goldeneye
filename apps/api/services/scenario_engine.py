"""
Scenario engine: applies shock list to baseline forecast context, re-runs models,
returns the result block per docs/API_CONTRACTS.md §scenarios.
"""
from __future__ import annotations

import copy
from dataclasses import replace

from apps.api.services.ensemble import compute_ensemble
from apps.api.services.llm_explainer import narrate_scenario
from apps.api.services.model_registry import ForecastContext, run_all


def apply(
    shocks: list[dict],  # type: ignore[type-arg]
    baseline_ctx: ForecastContext,
) -> tuple[ForecastContext, list[str], int]:
    """
    Apply shocks composably to a baseline ForecastContext.

    Later shocks compose on the output of earlier ones (e.g. two weather shocks both
    contribute to the cumulative weather_anomaly; two production shocks both reduce
    closes). Returns (shocked_ctx, assumptions, max_days).

    Shock types and their application logic:
    - type="weather":     weather_anomaly += shock["delta_temp_f"]
    - type="production":  closes adjusted downward by delta_bcfd * 0.01 per day
                          (production increase → price headwind heuristic)
    - type="lng_export":  closes adjusted upward by delta_bcfd * 0.01
                          (export increase → demand increase → price tailwind)
    - type="storage":     latest_storage["delta"] adjusted by shock["delta_bcf"]
    """
    shocked_closes = list(baseline_ctx.closes)
    shocked_weather = baseline_ctx.weather_anomaly or 0.0
    shocked_storage = (
        copy.deepcopy(baseline_ctx.latest_storage) if baseline_ctx.latest_storage else {}
    )

    max_days = 0
    assumptions: list[str] = []

    for shock in shocks:
        shock_type = shock.get("type", "")
        days = int(shock.get("days", 7))
        max_days = max(max_days, days)

        if shock_type == "weather":
            delta_temp = float(shock.get("delta_temp_f", 0.0))
            shocked_weather += delta_temp
            region = shock.get("region", "US national")
            assumptions.append(
                f"Cold air mass of {delta_temp:+.1f}°F persists for {days} days in {region}."
            )

        elif shock_type == "production":
            delta_bcfd = float(shock.get("delta_bcfd", 0.0))
            # Price impact heuristic: production increase → price headwind (small per-day reduction)
            price_impact = delta_bcfd * 0.01
            shocked_closes = [c - price_impact for c in shocked_closes]
            assumptions.append(
                f"Production changes by {delta_bcfd:+.2f} Bcf/d for {days} days, "
                f"applying a {price_impact:.4f}/MMBtu price headwind heuristic."
            )

        elif shock_type == "lng_export":
            delta_bcfd = float(shock.get("delta_bcfd", 0.0))
            # Export increase → demand increase → price tailwind
            price_impact = delta_bcfd * 0.01
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"LNG export demand changes by {delta_bcfd:+.2f} Bcf/d for {days} days, "
                f"applying a {price_impact:.4f}/MMBtu price tailwind heuristic."
            )

        elif shock_type == "storage":
            delta_bcf = float(shock.get("delta_bcf", 0.0))
            if isinstance(shocked_storage, dict):
                current = shocked_storage.get("delta", 0.0) or 0.0
                shocked_storage["delta"] = current + delta_bcf
            assumptions.append(
                f"Storage injection/withdrawal shifts by {delta_bcf:+.1f} Bcf "
                f"over the next {days} days."
            )

    shocked_ctx = replace(
        baseline_ctx,
        closes=shocked_closes,
        weather_anomaly=shocked_weather,
        latest_storage=shocked_storage if shocked_storage else baseline_ctx.latest_storage,
    )

    return shocked_ctx, assumptions, max_days


async def run_scenario(
    name: str,
    instrument: str,
    shocks: list[dict],  # type: ignore[type-arg]
    baseline_ctx: ForecastContext,
) -> dict:  # type: ignore[type-arg]
    """
    Apply shocks to a baseline ForecastContext, re-run the model suite, compute the ensemble,
    and generate a narrative.

    Returns a result dict per docs/API_CONTRACTS.md §scenarios.
    """
    # Apply shocks composably to the baseline context
    shocked_ctx, assumptions, max_days = apply(shocks, baseline_ctx)

    # Run models on baseline and shocked contexts
    baseline_results = await run_all(baseline_ctx)
    shocked_results = await run_all(shocked_ctx)

    baseline_ensemble = compute_ensemble(baseline_results)
    shocked_ensemble = compute_ensemble(shocked_results)

    # Delta in direction
    b_dir = baseline_ensemble["direction"]
    s_dir = shocked_ensemble["direction"]
    if s_dir == b_dir:
        delta_direction = f"unchanged ({s_dir})"
    else:
        delta_direction = f"shifted from {b_dir} to {s_dir}"

    # Delta in expected range
    b_range = baseline_ensemble.get("range", {})
    s_range = shocked_ensemble.get("range", {})
    delta_range: dict[str, float] = {
        "low_pct": (s_range.get("low_pct") or 0.0) - (b_range.get("low_pct") or 0.0),
        "high_pct": (s_range.get("high_pct") or 0.0) - (b_range.get("high_pct") or 0.0),
    }

    # Affected timeframe
    if max_days <= 7:
        affected_timeframe = "1 week"
    elif max_days <= 14:
        affected_timeframe = "2 weeks"
    elif max_days <= 30:
        affected_timeframe = "1 month"
    else:
        affected_timeframe = f"{max_days} days"

    # Standard counterarguments and validation signals based on dominant shock type —
    # these are deterministic, NOT LLM-generated (per docs/PHASE_06_PLAN.md §override 3).
    shock_types = {s.get("type", "") for s in shocks}
    counterarguments = _standard_counterarguments(shock_types, s_dir)
    data_needed = _standard_validation_data(shock_types)

    # Build narrative context
    narrate_results = {
        "baseline": baseline_ensemble,
        "shocked": shocked_ensemble,
        "delta_direction": delta_direction,
        "delta_range": delta_range,
    }
    narrate_ctx: dict = {"instrument": instrument}  # type: ignore[type-arg]

    narrative_text, safety_envelope = await narrate_scenario(
        {"name": name, "shocks": shocks},
        narrate_results,
        narrate_ctx,
    )

    return {
        "directional_pressure": shocked_ensemble["direction"],
        "confidence": shocked_ensemble["confidence"],
        "affected_timeframe": affected_timeframe,
        "expected_pct_range": {
            "low": shocked_ensemble["range"]["low_pct"] if shocked_ensemble.get("range") else -0.02,
            "high": shocked_ensemble["range"]["high_pct"] if shocked_ensemble.get("range") else 0.02,
        },
        "assumptions": assumptions,
        "counterarguments": counterarguments,
        "data_needed_to_validate": data_needed,
        "narrative": narrative_text,
        "safety": safety_envelope.model_dump(),
    }


def _standard_counterarguments(shock_types: set[str], direction: str) -> list[str]:
    """Return 2-3 standard counterarguments for the given shock types."""
    args: list[str] = []

    if "weather" in shock_types:
        args.append(
            "Weather forecasts beyond 7 days carry significant uncertainty; the market may "
            "already be partially pricing in the temperature anomaly."
        )

    if "production" in shock_types or "lng_export" in shock_types:
        args.append(
            "Supply-side adjustments typically lag price signals by 30-60 days; near-term "
            "price impact may be muted while the market awaits confirmation."
        )

    if "storage" in shock_types:
        args.append(
            "A single storage report deviation is often revised in subsequent weeks; "
            "a single data point is insufficient to confirm a structural shift."
        )

    # Always include a generic counterargument
    args.append(
        "Speculative positioning is extended in the current COT report; crowded positioning "
        "could amplify a reversal if the scenario fails to materialize."
    )

    return args[:3]


def _standard_validation_data(shock_types: set[str]) -> list[str]:
    """Return 3-4 standard data validation signals for the given shock types."""
    signals: list[str] = [
        "Next EIA Weekly Natural Gas Storage Report (Thursdays) for storage trajectory confirmation.",
    ]

    if "weather" in shock_types:
        signals.append(
            "NWS 6-10 day and 8-14 day temperature anomaly maps for persistence of the "
            "temperature shock."
        )

    if "production" in shock_types:
        signals.append(
            "Lower-48 dry gas production data (EIA weekly estimates) to confirm output change."
        )

    if "lng_export" in shock_types:
        signals.append(
            "LNG feed-gas nominations (daily) from Platts/Genscape to confirm export demand shift."
        )

    signals.append(
        "Front-month vs. 12-month strip spread as a real-time market-implied read on "
        "scenario credibility."
    )

    return signals[:4]
