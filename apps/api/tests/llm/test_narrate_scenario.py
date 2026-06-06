"""
LLM corpus eval for narrate_scenario.

For each scenario template, we provide a plausible fixture narrative response.
The test verifies:
1. The inference-marker regex matches (institutional hedged tone).
2. All 5 required narrative sections are detectable via keyword regex.
3. scan_for_forbidden returns False (zero violations).

This is a static-corpus test — it does NOT call a live LLM. A separate
`pytest -m llm_live` corpus can be added later for end-to-end runs.
"""
from __future__ import annotations

import re

import pytest

from apps.api.services.safety import scan_for_forbidden

# ---------------------------------------------------------------------------
# Regex matchers
# ---------------------------------------------------------------------------
INFERENCE_RE = re.compile(
    r"\b(appears|suggests|reads as|consistent with)\b",
    re.IGNORECASE,
)

# Section 1 — what the scenario assumes
SECTION_1_RE = re.compile(r"\b(assume|assumes|assumption|assuming)\b", re.IGNORECASE)
# Section 2 — how the data would shift
SECTION_2_RE = re.compile(
    r"\b(shift|would shift|play out|plays out|materialize|materializes)\b",
    re.IGNORECASE,
)
# Section 3 — directional pressure + confidence band + timeframe
SECTION_3_RE = re.compile(
    r"\b(directional pressure|bullish|bearish|neutral)\b",
    re.IGNORECASE,
)
CONFIDENCE_BAND_RE = re.compile(
    r"\b(low|moderate|medium|high)\s+confidence\b",
    re.IGNORECASE,
)
# Section 4 — strongest counterargument
SECTION_4_RE = re.compile(
    r"\b(however|counter|counterargument|caveat|less convincing)\b",
    re.IGNORECASE,
)
# Section 5 — data that would validate or invalidate
SECTION_5_RE = re.compile(r"\b(validate|invalidate|confirm)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Fixture responses — one per template. Each is a 4-6 sentence institutional
# narrative covering all 5 required sections.
# ---------------------------------------------------------------------------
FIXTURE_RESPONSES: dict[str, str] = {
    "cold_snap_northeast": (
        "The scenario assumes a 10-day cold air mass over the Northeast and Midwest, with -12°F "
        "and -6°F anomalies respectively. If this plays out, the data would shift toward higher "
        "residential and commercial heating burn, particularly in the gas-weighted Northeast. "
        "This reads as bullish directional pressure with moderate confidence over a 1-2 week "
        "timeframe. However, the strongest counterargument is that the market may have already "
        "priced in part of the temperature anomaly; weather forecasts beyond 7 days carry "
        "significant uncertainty. Data that would validate the scenario: NWS 6-10 day temperature "
        "anomaly maps and the EIA weekly storage report on Thursday."
    ),
    "lng_export_disruption": (
        "The scenario assumes a 14-day Gulf Coast LNG terminal outage reducing exports by 2.1 "
        "Bcf/d. If the outage materializes, the data would shift toward looser near-term balances "
        "as displaced gas re-enters domestic supply. This appears consistent with bearish "
        "directional pressure with moderate confidence over a 1-2 week timeframe. However, the "
        "counterargument is that operators may compensate via increased storage injections, "
        "muting the price signal. The next EIA weekly storage report and daily LNG feed-gas "
        "nominations would validate or invalidate this read."
    ),
    "appalachia_freeze_off": (
        "The scenario assumes Appalachian freeze-offs reduce dry gas production by 3.5 Bcf/d for "
        "roughly one week, coinciding with a -18°F regional temperature anomaly. If this scenario "
        "plays out, supply would shift lower while demand remains elevated. This reads as bullish "
        "directional pressure with moderate confidence on a 1-week horizon. However, the "
        "counterargument is that freeze-offs typically recover within days, and the market often "
        "discounts the supply impact. Lower-48 dry gas production estimates from EIA and NWS "
        "temperature persistence maps would confirm or invalidate the scenario."
    ),
    "hurricane_gulf_coast": (
        "The scenario assumes a major Gulf hurricane forces production shut-ins (-5 Bcf/d for 5 "
        "days, lingering -2 Bcf/d for 14 days) and partially curtails LNG feed-gas. The data "
        "would shift toward tighter near-term balances as offshore output stalls and exports "
        "drop. This appears consistent with bullish directional pressure but only low confidence, "
        "given the binary path-dependence and a 1-2 week timeframe. However, the counterargument "
        "is that Gulf production has structurally declined as a share of US output, and recovery "
        "tends to be faster than in prior cycles. NHC track updates, platform shut-in surveys, "
        "and EIA storage prints would validate or invalidate the scenario."
    ),
    "geopolitical_europe_demand": (
        "The scenario assumes a European pipeline disruption drives a surge in spot LNG demand, "
        "pulling +3.2 Bcf/d of additional US exports for 21 days while drawing -45 Bcf from "
        "storage. If this plays out, the data would shift toward tighter balances and a wider "
        "trans-Atlantic spread. This reads as bullish directional pressure with moderate "
        "confidence over a 2-3 week timeframe. However, the counterargument is that US export "
        "infrastructure is near capacity, limiting how much additional flow can physically be "
        "delivered. TTF-Henry Hub spreads and EIA weekly LNG feed-gas data would validate or "
        "invalidate the scenario."
    ),
    "heat_wave_national": (
        "The scenario assumes a sustained heat wave across the Southeast, South Central, and "
        "Midwest with +7 to +10°F anomalies over 10-12 days. If the heat wave materializes, the "
        "data would shift toward elevated power-sector gas burn beyond seasonal norms. This "
        "appears consistent with bullish directional pressure on a moderate confidence band over "
        "a 1-2 week timeframe. However, the counterargument is that high renewables output and "
        "coal-to-gas elasticity could blunt the burn impulse. NWS temperature anomaly maps and "
        "ERCOT/MISO daily gen-mix data would confirm or invalidate the scenario."
    ),
    "opec_surprise_cut": (
        "The scenario assumes OPEC+ delivers an unscheduled 1.5 Mb/d production cut sustained over "
        "roughly a quarter. If the cut materializes, balances would shift tighter as seaborne "
        "supply is withdrawn. This reads as bullish directional pressure with moderate confidence "
        "over a multi-week timeframe. However, the counterargument is that OPEC+ compliance is "
        "historically imperfect and announced cuts often exceed realized ones. OPEC+ JMMC "
        "communiques and Argus/Platts realized-production estimates would validate or invalidate "
        "the scenario."
    ),
    "hormuz_disruption": (
        "The scenario assumes an escalation threatens transit through the Strait of Hormuz, "
        "removing roughly 3 Mb/d from the seaborne market alongside a modest inventory draw. If "
        "flows are interrupted, the data would shift toward a wider risk premium and tighter "
        "prompt balances. This appears consistent with bullish directional pressure, though only "
        "low confidence given the binary, headline-driven path. However, the counterargument is "
        "that risk premia decay quickly when physical flows are not actually interrupted. "
        "Tanker-tracking through the chokepoint and insurance and freight-rate moves would "
        "confirm or invalidate the scenario."
    ),
    "china_demand_slowdown": (
        "The scenario assumes a sharper-than-expected Chinese slowdown cuts apparent oil demand by "
        "about 1.8 Mb/d for two months. If demand softens as assumed, balances would shift looser "
        "into the back half of the year. This reads as bearish directional pressure with moderate "
        "confidence over a multi-week timeframe. However, the counterargument is that Chinese "
        "demand estimates are revised substantially and high-frequency refinery-run data may not "
        "confirm the shift. China apparent-demand data and IEA/EIA monthly revisions would "
        "validate or invalidate the scenario."
    ),
    "coordinated_spr_release": (
        "The scenario assumes IEA members announce a coordinated SPR release adding roughly 60 "
        "MMbbl of government barrels over a month. If the release plays out, available supply "
        "would shift higher and cap prompt prices. This appears consistent with bearish "
        "directional pressure with low confidence, as SPR actions are finite and partly "
        "anticipated. However, the counterargument is that a single release is a one-off that the "
        "curve may already discount. Weekly EIA crude stocks and DOE SPR level updates would "
        "confirm or invalidate the scenario."
    ),
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
TEMPLATE_IDS = list(FIXTURE_RESPONSES.keys())


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_no_forbidden_phrases(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert not scan_for_forbidden(response), (
        f"{template_id}: forbidden phrase found in fixture response."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_inference_marker(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert INFERENCE_RE.search(response), (
        f"{template_id}: no inference marker (appears/suggests/reads as/consistent with) found."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_section_1_assumptions(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert SECTION_1_RE.search(response), (
        f"{template_id}: missing section 1 (assumptions) marker."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_section_2_data_shift(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert SECTION_2_RE.search(response), (
        f"{template_id}: missing section 2 (data shift) marker."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_section_3_direction_and_confidence(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert SECTION_3_RE.search(response), (
        f"{template_id}: missing section 3 (directional pressure) marker."
    )
    assert CONFIDENCE_BAND_RE.search(response), (
        f"{template_id}: missing confidence band in section 3."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_section_4_counterargument(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert SECTION_4_RE.search(response), (
        f"{template_id}: missing section 4 (counterargument) marker."
    )


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_fixture_has_section_5_validation(template_id: str) -> None:
    response = FIXTURE_RESPONSES[template_id]
    assert SECTION_5_RE.search(response), (
        f"{template_id}: missing section 5 (validate/invalidate) marker."
    )


def test_fixture_covers_all_templates() -> None:
    """Sanity: the fixture set covers every id in packages/fixtures/scenario_templates.json."""
    import json
    from pathlib import Path

    fixtures_path = (
        Path(__file__).resolve().parents[4]
        / "packages"
        / "fixtures"
        / "scenario_templates.json"
    )
    templates = json.loads(fixtures_path.read_text())
    template_ids = {t["id"] for t in templates}
    assert template_ids == set(FIXTURE_RESPONSES.keys()), (
        f"Template ids mismatch. Templates: {template_ids}. Fixtures: {set(FIXTURE_RESPONSES)}."
    )
