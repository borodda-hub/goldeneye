"""Tests that scan_for_forbidden correctly catches all forbidden phrases."""
from __future__ import annotations

from datetime import datetime

import pytest

from apps.api.services.safety import DISCLAIMER, SafetyEnvelope, scan_for_forbidden, wrap_with_uncertainty


@pytest.mark.parametrize(
    "phrase",
    [
        "this is guaranteed to work",
        "you will profit from this",
        "sure thing for tomorrow",
        "it is risk-free",
        "no risk involved",
        "buy now before it is too late",
        "sell now at peak",
        "go long on NG",
        "go short on NG",
        "you should buy this",
        "you should sell immediately",
        "i recommend buying",
        "my recommendation is bullish",
        "this is a buy signal",
        "this is a sell signal",
        "hot tip from our desk",
        "moonshot potential",
        "to the moon",
        "price will hit $4.50 next week",
        "going to reach $5",
    ],
)
def test_forbidden_phrases_detected(phrase: str) -> None:
    assert scan_for_forbidden(phrase) is True, f"Expected violation for: {phrase!r}"


@pytest.mark.parametrize(
    "clean",
    [
        "The data suggests moderate bullish pressure.",
        "Storage appears below the 5-year average, however warm weather could reverse this.",
        "Confidence is medium with the caveat that LNG data is lagging.",
        "This reads as a cautious setup with contradicting evidence from COT positioning.",
    ],
)
def test_clean_text_passes(clean: str) -> None:
    assert scan_for_forbidden(clean) is False, f"Expected clean for: {clean!r}"


def test_wrap_with_uncertainty() -> None:
    envelope = wrap_with_uncertainty(
        {}, confidence="medium", caveats=["Test caveat"], as_of=datetime.utcnow()
    )
    assert isinstance(envelope, SafetyEnvelope)
    assert envelope.confidence == "medium"
    assert envelope.disclaimer == DISCLAIMER


def test_disclaimer_content() -> None:
    assert "research" in DISCLAIMER.lower()
    assert "financial advice" in DISCLAIMER.lower()
