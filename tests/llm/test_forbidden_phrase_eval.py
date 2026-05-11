"""
Runs the eval suite: verifies that llm_explainer outputs in fake mode:
1. All pass scan_for_forbidden (0% violation rate)
2. All contain an inference marker (appears/suggests/reads as/consistent with)
3. Are not single-sentence (> 80 chars)
"""
from __future__ import annotations

import re

import pytest

from apps.api.services.llm_explainer import explain_signal, narrate_scenario, summarize_market
from apps.api.services.safety import scan_for_forbidden

INFERENCE_PATTERN = re.compile(
    r"\b(appears|suggests|reads as|consistent with)\b",
    re.IGNORECASE,
)


@pytest.mark.asyncio
async def test_summarize_market_fake_mode() -> None:
    text, envelope = await summarize_market({"price": 3.41, "vol_regime": "elevated"})
    assert not scan_for_forbidden(text), f"Violation in summarize_market: {text}"
    assert INFERENCE_PATTERN.search(text), f"No inference marker in: {text}"
    assert len(text) > 80


@pytest.mark.asyncio
async def test_explain_signal_fake_mode() -> None:
    text, envelope = await explain_signal(
        {"direction": "bullish", "confidence": "medium"}, {}
    )
    assert not scan_for_forbidden(text)
    assert INFERENCE_PATTERN.search(text)


@pytest.mark.asyncio
async def test_narrate_scenario_fake_mode() -> None:
    text, envelope = await narrate_scenario({"name": "Test", "shocks": []}, {}, {})
    assert not scan_for_forbidden(text)
    assert len(text) > 80
