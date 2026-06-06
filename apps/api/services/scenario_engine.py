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

    Each shock both records itself on its native field AND translates into a
    price-impact heuristic on `closes`, so the models (which read `closes`
    plus optional alt-data) actually see the shock. Prior to this fix,
    weather and storage shocks only wrote to fields no model consumed —
    changing shock values produced identical forecasts.

    Heuristics (rough magnitudes; not calibrated to historical sensitivities):

    - type="weather":     each 1°F of anomaly → -0.005/MMBtu (cold = up).
                          Scaled by days / 7 so a longer event has more impact.
                          Also accumulates into weather_anomaly.

    - type="production":  each 1 Bcf/d → -0.01/MMBtu (more supply = down).
                          Scaled by days / 7.

    - type="lng_export":  each 1 Bcf/d → +0.01/MMBtu (more exports = up).
                          Scaled by days / 7.

    - type="storage":     writes delta_vs_consensus on latest_storage so the
                          factor composite sees it (positive = larger build
                          than expected = bearish in the composite's logic).
                          Also accumulates into closes via a small price
                          heuristic so even price-only models register it.
    """
    # Tunable magnitudes — kept in one place so backtests can sweep them.
    # Natural gas ($/MMBtu):
    WEATHER_PRICE_PER_DEG_F = -0.005   # cold (negative ΔT) → price up
    PRODUCTION_PRICE_PER_BCFD = -0.01  # supply ↑ → price ↓
    LNG_EXPORT_PRICE_PER_BCFD = 0.01   # demand ↑ → price ↑
    STORAGE_PRICE_PER_BCF = -0.0005    # bigger build vs consensus = bearish
    # Crude oil ($/bbl) — rough magnitudes, not calibrated sensitivities:
    OPEC_SUPPLY_PRICE_PER_MBPD = -3.0   # OPEC+ cut (negative) → price up
    GEO_SUPPLY_PRICE_PER_MBPD = -4.0    # outage (negative) → price up (risk premium)
    DEMAND_PRICE_PER_MBPD = 3.0         # more demand → price up
    INVENTORY_PRICE_PER_MMBBL = -0.05   # bigger build / SPR release → price down

    shocked_closes = list(baseline_ctx.closes)
    shocked_weather = baseline_ctx.weather_anomaly or 0.0
    # Always start from a dict — storage shocks need somewhere to write the
    # delta_vs_consensus key even when the baseline context has no storage data.
    shocked_storage: dict = (
        copy.deepcopy(baseline_ctx.latest_storage)
        if isinstance(baseline_ctx.latest_storage, dict)
        else {}
    )

    max_days = 0
    assumptions: list[str] = []

    for shock in shocks:
        shock_type = shock.get("type", "")
        days = int(shock.get("days", 7))
        max_days = max(max_days, days)
        # Persistence multiplier — a 14-day event has ~2× the cumulative
        # impact of a 7-day one. Capped so a 60-day shock isn't 8×.
        days_factor = min(days / 7.0, 4.0)

        if shock_type == "weather":
            delta_temp = float(shock.get("delta_temp_f", 0.0))
            shocked_weather += delta_temp
            region = shock.get("region", "US national")
            price_impact = delta_temp * WEATHER_PRICE_PER_DEG_F * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Temperature anomaly of {delta_temp:+.1f}°F persists for {days} days "
                f"in {region}, applying a {price_impact:+.4f}/MMBtu price-impact "
                f"heuristic to all closes."
            )

        elif shock_type == "production":
            delta_bcfd = float(shock.get("delta_bcfd", 0.0))
            price_impact = delta_bcfd * PRODUCTION_PRICE_PER_BCFD * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Production changes by {delta_bcfd:+.2f} Bcf/d for {days} days, "
                f"applying a {price_impact:+.4f}/MMBtu price impact (supply heuristic)."
            )

        elif shock_type == "lng_export":
            delta_bcfd = float(shock.get("delta_bcfd", 0.0))
            price_impact = delta_bcfd * LNG_EXPORT_PRICE_PER_BCFD * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"LNG export demand changes by {delta_bcfd:+.2f} Bcf/d for {days} days, "
                f"applying a {price_impact:+.4f}/MMBtu price impact (demand heuristic)."
            )

        elif shock_type == "storage":
            delta_bcf = float(shock.get("delta_bcf", 0.0))
            # Field name that factor_composite actually reads.
            existing = shocked_storage.get("delta_vs_consensus", 0.0) or 0.0
            shocked_storage["delta_vs_consensus"] = existing + delta_bcf
            # Also nudge closes so price-only models see something.
            price_impact = delta_bcf * STORAGE_PRICE_PER_BCF * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Storage delta vs consensus shifts by {delta_bcf:+.1f} Bcf over "
                f"{days} days, applying a {price_impact:+.4f}/MMBtu price-impact "
                f"heuristic to closes and surfacing the delta on the composite input."
            )

        elif shock_type == "opec_supply":
            delta_mbpd = float(shock.get("delta_mbpd", 0.0))
            price_impact = delta_mbpd * OPEC_SUPPLY_PRICE_PER_MBPD * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"OPEC+ output changes by {delta_mbpd:+.2f} Mb/d for {days} days, "
                f"applying a {price_impact:+.3f}/bbl price impact (a cut tightens balances)."
            )

        elif shock_type == "geopolitical_supply":
            delta_mbpd = float(shock.get("delta_mbpd", 0.0))
            region = shock.get("region", "global")
            price_impact = delta_mbpd * GEO_SUPPLY_PRICE_PER_MBPD * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Geopolitical supply shift of {delta_mbpd:+.2f} Mb/d via {region} for "
                f"{days} days, applying a {price_impact:+.3f}/bbl price impact "
                f"(an outage adds a risk premium)."
            )

        elif shock_type == "demand":
            delta_mbpd = float(shock.get("delta_mbpd", 0.0))
            region = shock.get("region", "global")
            price_impact = delta_mbpd * DEMAND_PRICE_PER_MBPD * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Oil demand changes by {delta_mbpd:+.2f} Mb/d in {region} for {days} days, "
                f"applying a {price_impact:+.3f}/bbl price impact (demand heuristic)."
            )

        elif shock_type == "inventory":
            delta_mmbbl = float(shock.get("delta_mmbbl", 0.0))
            price_impact = delta_mmbbl * INVENTORY_PRICE_PER_MMBBL * days_factor
            shocked_closes = [c + price_impact for c in shocked_closes]
            assumptions.append(
                f"Available crude stocks shift by {delta_mmbbl:+.1f} MMbbl over {days} days "
                f"(a build or SPR release adds supply), applying a {price_impact:+.3f}/bbl "
                f"price-impact heuristic to closes."
            )

    shocked_ctx = replace(
        baseline_ctx,
        closes=shocked_closes,
        weather_anomaly=shocked_weather,
        # Pass the dict even when empty — keeps the storage path consistent.
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
    counterarguments = _standard_counterarguments(shock_types, s_dir, instrument)
    data_needed = _standard_validation_data(shock_types, instrument)

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
        # mode="json" ISO-formats datetimes — required because the caller
        # persists this dict into the scenario_runs.result JSONB column, and
        # asyncpg's default JSON serializer can't handle raw datetimes.
        "safety": safety_envelope.model_dump(mode="json"),
    }


def _standard_counterarguments(
    shock_types: set[str], direction: str, instrument: str = "NG"
) -> list[str]:
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

    # --- crude oil shock types ---
    if "opec_supply" in shock_types:
        args.append(
            "OPEC+ compliance is historically imperfect; announced cuts often exceed realized "
            "cuts, and spare capacity can be redeployed if prices overshoot."
        )

    if "geopolitical_supply" in shock_types:
        args.append(
            "Geopolitical risk premia decay quickly when physical flows are not actually "
            "interrupted; the market frequently fades the headline within days."
        )

    if "demand" in shock_types:
        args.append(
            "Demand estimates — China especially — are revised substantially; high-frequency "
            "refinery-run and mobility data may not confirm the assumed shift."
        )

    if "inventory" in shock_types:
        args.append(
            "A single inventory print is noisy and subject to revision, and SPR actions are "
            "finite and often partly anticipated by the curve."
        )

    # Always include a generic counterargument
    args.append(
        "Speculative positioning is extended in the current COT report; crowded positioning "
        "could amplify a reversal if the scenario fails to materialize."
    )

    return args[:3]


def _standard_validation_data(shock_types: set[str], instrument: str = "NG") -> list[str]:
    """Return 3-4 standard data validation signals for the given shock types."""
    is_crude = instrument in {"BZ", "CL"}
    if is_crude:
        signals: list[str] = [
            "Next EIA Weekly Petroleum Status Report (Wednesdays) and the OPEC+ monthly "
            "market report for inventory and output trajectory.",
        ]
    else:
        signals = [
            "Next EIA Weekly Natural Gas Storage Report (Thursdays) for storage trajectory "
            "confirmation.",
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

    # --- crude oil shock types ---
    if "opec_supply" in shock_types:
        signals.append(
            "OPEC+ JMMC communique plus Argus/Platts realized-production estimates to confirm "
            "the output change versus the headline."
        )

    if "geopolitical_supply" in shock_types:
        signals.append(
            "Tanker-tracking (Kpler/Vortexa) for actual flows through the affected chokepoint, "
            "plus insurance and freight-rate moves."
        )

    if "demand" in shock_types:
        signals.append(
            "China apparent demand (refinery throughput + net imports) and IEA/EIA monthly "
            "demand revisions."
        )

    if "inventory" in shock_types:
        signals.append(
            "Weekly EIA crude stocks and DOE SPR level updates; OECD commercial stock cover "
            "(days of forward demand)."
        )

    signals.append(
        "Front-month vs. 12-month strip spread as a real-time market-implied read on "
        "scenario credibility."
    )

    return signals[:4]
