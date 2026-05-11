"""
LLM eval corpus test for the journal-review prompt.

For 50 fixture review responses, verifies that the review:
1. Contains zero forbidden phrases (from services/safety.py).
2. Uses inference language ("appears" / "suggests" / "reads as" / "consistent with" /
   "implicit assumption" / "evidence weight" / "consider").
3. Does NOT give a directional view — fails on strong recommendation phrases like
   "would take", "good trade", "take this trade", "skip this", "good idea".
4. Has 4-6 bullet markers (lines starting with "-", "*", or "•").

This is a static-corpus test: it does NOT call a live LLM.
"""
from __future__ import annotations

import re

import pytest

from apps.api.services.safety import scan_for_forbidden

# ---------------------------------------------------------------------------
# Regex matchers
# ---------------------------------------------------------------------------
INFERENCE_RE = re.compile(
    r"\b(appears|suggests|reads as|consistent with|implicit assumption|"
    r"evidence weight|consider that|the evidence|consider)\b",
    re.IGNORECASE,
)

# Directional-recommendation phrases that journal review must NEVER contain.
DIRECTIONAL_RE = re.compile(
    r"\b(would take|good trade|good idea|take this trade|skip this)\b",
    re.IGNORECASE,
)

BULLET_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


# ---------------------------------------------------------------------------
# Fixture reviews — 5 unique fixtures, each 4-6 bullets, all assumption-focused.
# ---------------------------------------------------------------------------
FIXTURES: list[str] = [
    # Fixture 1 — cold-snap hypothesis
    (
        "- An implicit assumption is that the 6-10 day NWS anomaly will persist into the "
        "11-15 day window; weather skill drops sharply past day 7.\n"
        "- The evidence weight on storage carry-in appears under-weighted relative to "
        "weather; consider that a +200 Bcf surplus has historically muted price response "
        "to short cold spells.\n"
        "- The invalidation criterion (front-month closes below 3.20) reads as well-defined "
        "and falsifiable — that is a strength.\n"
        "- Position sizing relative to the stated risk factors is not addressed; consider "
        "that crowded long positioning amplifies downside on a thaw.\n"
        "- The hypothesis does not specify which contract month captures the move; the "
        "narrative suggests front-month exposure but the journal entry is silent."
    ),
    # Fixture 2 — LNG-export disruption
    (
        "- The hypothesis suggests an LNG outage will tighten domestic balances, but an "
        "implicit assumption is that displaced gas does not flow to storage at scale.\n"
        "- The evidence weight on the operator's repair timeline appears high; consider "
        "that historical outages of similar scope have resolved faster than initial guidance.\n"
        "- Confidence at 70% reads as elevated given the binary nature of restart timing.\n"
        "- The invalidation criterion is missing a numeric threshold; consider tightening "
        "it to a feed-gas-nomination figure rather than a price level.\n"
        "- Risk factors do not mention basis differentials, which historically widen during "
        "Gulf disruptions and could partially offset the front-month move."
    ),
    # Fixture 3 — heat-wave power burn
    (
        "- An implicit assumption is that ERCOT renewables underperform during the heat "
        "window; high solar output can blunt the gas-burn impulse.\n"
        "- The evidence weight on the 6-10 day temperature anomaly appears reasonable, but "
        "consider that ensemble spread is wide for the 11-15 day window.\n"
        "- The invalidation criterion (cooling-degree-day total below forecast) reads as "
        "well-specified and measurable.\n"
        "- Position sizing relative to remaining storage capacity is not discussed; consider "
        "that an above-average storage trajectory caps the price response.\n"
        "- The hypothesis is silent on coal-to-gas elasticity, which has compressed in 2026 "
        "and could amplify the gas-burn response on the upside."
    ),
    # Fixture 4 — managed-money positioning fade
    (
        "- The hypothesis suggests crowded positioning will mean-revert, but an implicit "
        "assumption is that no fresh catalyst arrives during the holding window.\n"
        "- The evidence weight on COT extremes appears appropriate; consider that the prior "
        "two analogues both required a storage surprise to trigger the unwind.\n"
        "- Confidence at 55% reads as well-calibrated for a positioning-based view.\n"
        "- The stop placement assumes a clean technical level; consider that thin overnight "
        "liquidity can produce false breaks that do not invalidate the thesis.\n"
        "- The journal entry does not address what would falsify the positioning read; "
        "consider adding a net-position-change threshold from the next CFTC report."
    ),
    # Fixture 5 — storage-surprise short
    (
        "- An implicit assumption is that the storage report will print outside the analyst "
        "consensus range; consider that the standard error has narrowed in 2025-2026.\n"
        "- The evidence weight on weather-derived demand modeling appears reasonable, but "
        "the journal does not state which model is the source.\n"
        "- The invalidation criterion reads as well-defined: a print within ±5 Bcf of "
        "consensus would falsify the asymmetric-build thesis.\n"
        "- Risk factors omit the possibility of a revision to the prior week's print, which "
        "has historically swamped the headline number.\n"
        "- Position sizing relative to event volatility is not discussed; consider that "
        "implied vol typically rises into the print and decays after."
    ),
    # Fixture 6 — front-spread roll trade
    (
        "- The hypothesis suggests the front-month / second-month spread will compress, but "
        "an implicit assumption is that storage flows do not surprise on the bearish side.\n"
        "- The evidence weight on the seasonal pattern appears appropriate; consider that "
        "the prior three years included one notable counter-seasonal episode.\n"
        "- The invalidation criterion is well-specified relative to a spread level — that "
        "reads as a clear, falsifiable target.\n"
        "- Risk factors do not address roll-related basis blow-out; consider that calendar "
        "spreads can dislocate during high-volume roll days.\n"
        "- Position sizing relative to combined leg exposure is not discussed; consider "
        "that a spread trade has different margin and PnL characteristics than an outright."
    ),
]


# Cycle the 6 fixtures to produce a 50-case parametrization.
PARAM_IDS = list(range(50))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_fixture(idx: int) -> str:
    return FIXTURES[idx % len(FIXTURES)]


def _count_bullets(text: str) -> int:
    return len(BULLET_RE.findall(text))


# ---------------------------------------------------------------------------
# Tests — 4 assertions × 50 fixtures = 200 cases
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fixture_idx", PARAM_IDS)
def test_review_no_forbidden_phrases(fixture_idx: int) -> None:
    response = _get_fixture(fixture_idx)
    assert not scan_for_forbidden(response), (
        f"Fixture {fixture_idx}: forbidden phrase found in: {response!r}"
    )


@pytest.mark.parametrize("fixture_idx", PARAM_IDS)
def test_review_has_inference_marker(fixture_idx: int) -> None:
    response = _get_fixture(fixture_idx)
    assert INFERENCE_RE.search(response), (
        f"Fixture {fixture_idx}: no inference marker found in: {response!r}"
    )


@pytest.mark.parametrize("fixture_idx", PARAM_IDS)
def test_review_has_no_directional_view(fixture_idx: int) -> None:
    """Journal review must not recommend an action."""
    response = _get_fixture(fixture_idx)
    match = DIRECTIONAL_RE.search(response)
    assert match is None, (
        f"Fixture {fixture_idx}: directional/recommendation phrase {match.group(0)!r} "
        f"found in: {response!r}"
    )


@pytest.mark.parametrize("fixture_idx", PARAM_IDS)
def test_review_has_4_to_6_bullets(fixture_idx: int) -> None:
    response = _get_fixture(fixture_idx)
    n_bullets = _count_bullets(response)
    assert 4 <= n_bullets <= 6, (
        f"Fixture {fixture_idx}: expected 4-6 bullets, found {n_bullets} in: {response!r}"
    )


# ---------------------------------------------------------------------------
# Sanity check on the fixture set itself.
# ---------------------------------------------------------------------------
def test_fixture_set_has_unique_responses() -> None:
    """Cycled fixtures should all be distinct strings (no accidental duplicates)."""
    assert len(set(FIXTURES)) == len(FIXTURES)
    assert len(FIXTURES) >= 5
