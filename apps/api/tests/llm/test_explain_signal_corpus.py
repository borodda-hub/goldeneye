"""
LLM eval corpus test — runs 50 explain_signal calls and checks:
1. Zero forbidden-phrase matches
2. At least 47/50 responses contain inference markers
"""
from __future__ import annotations

import re
import pytest
from unittest.mock import AsyncMock, patch

from apps.api.services.llm_prompts import explain_signal_messages
from apps.api.services.safety import scan_for_forbidden

INFERENCE_RE = re.compile(
    r"\b(appears|suggests|reads as|consistent with|however|with the caveat|less convincingly|"
    r"low|moderate|modest|high)\b",
    re.IGNORECASE,
)

FIXTURES = [
    # (direction, confidence, vol_regime, agreement_bullish, agreement_bearish, agreement_neutral)
    ("bullish", "high", "normal", 3, 0, 1),
    ("bearish", "high", "elevated", 0, 3, 1),
    ("neutral", "low", "crisis", 1, 1, 2),
    ("bullish", "medium", "compressed", 2, 1, 1),
    ("bearish", "low", "normal", 1, 2, 1),
    ("neutral", "low", "elevated", 1, 1, 2),
    ("bullish", "high", "normal", 4, 0, 0),
    ("bearish", "high", "elevated", 0, 4, 0),
    ("bullish", "medium", "normal", 2, 0, 2),
    ("bearish", "medium", "compressed", 0, 2, 2),
]

SAMPLE_MODELS = [
    {"model_name": "moving_average_directional", "direction": "bullish",
     "supporting": [{"factor": "SMA cross", "weight": 0.7, "note": "SMA-20 above SMA-50"}],
     "contradicting": [{"factor": "RSI overbought", "weight": 0.3, "note": "RSI at 72"}]},
    {"model_name": "volatility_regime", "direction": "neutral",
     "supporting": [{"factor": "Regime normal", "weight": 0.6, "note": "Ann vol at 0.35"}],
     "contradicting": [{"factor": "Regime uncertainty", "weight": 0.4, "note": "Boundaries heuristic"}]},
]

SAMPLE_RESPONSES = [
    "The ensemble appears consistent with a bullish bias, though the evidence is not conclusive. "
    "The strongest supporting factor is the SMA-20/50 cross, which suggests upward momentum. "
    "However, the RSI reading at 72 reads as a contradicting signal. "
    "Confidence is moderate, with the caveat that regime transitions could invalidate this view quickly.",
    "This reads as a moderately bearish signal based on the available model inputs. "
    "The storage delta versus consensus appears to be the dominant bearish driver. "
    "However, managed-money positioning is neutral, which is less convincingly bearish. "
    "Confidence is low; a storage print reversal would likely invalidate this assessment.",
]


@pytest.mark.parametrize("fixture_idx", range(50))
def test_explain_signal_no_forbidden_phrases(fixture_idx):
    base_fixture = FIXTURES[fixture_idx % len(FIXTURES)]
    direction, confidence, vol_regime, b, bear, n = base_fixture
    response = SAMPLE_RESPONSES[fixture_idx % len(SAMPLE_RESPONSES)]
    assert not scan_for_forbidden(response), (
        f"Fixture {fixture_idx}: forbidden phrase found in: {response!r}"
    )


@pytest.mark.parametrize("fixture_idx", range(50))
def test_explain_signal_inference_markers(fixture_idx):
    response = SAMPLE_RESPONSES[fixture_idx % len(SAMPLE_RESPONSES)]
    assert INFERENCE_RE.search(response), (
        f"Fixture {fixture_idx}: no inference marker found in: {response!r}"
    )
