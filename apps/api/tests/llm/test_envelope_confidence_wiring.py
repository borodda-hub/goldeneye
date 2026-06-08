"""Phase A2 — wiring test: the three forecast-bearing LLM narratives surface the
*derived* envelope confidence (passed in by the router), not the old hardcoded "medium".

Runs in the default fake LLM mode (deterministic canned responses); no network/DB.
"""
from __future__ import annotations

import inspect

import pytest

from apps.api.services import llm_explainer
from apps.api.services.ensemble import derive_envelope_confidence
from apps.api.services.llm_explainer import (
    explain_signal,
    generate_thesis,
    summarize_market,
)


@pytest.fixture(autouse=True)
def _clear_llm_caches():
    """Each test starts with empty explainer caches so envelope values aren't stale."""
    llm_explainer._cache.clear()
    llm_explainer._thesis_cache.clear()
    yield


def _signal(**over):
    base = {
        "direction": "bullish",
        "confidence": "high",
        "vol_regime": "normal",
        "agreement": {"bullish": 4, "bearish": 0, "neutral": 0, "total": 4,
                      "input_diversity": "low"},
        "confidence_rationale": ["4 of 4 models agree on bullish direction."],
        "models": [],
    }
    base.update(over)
    return base


async def test_explain_signal_surfaces_passed_confidence():
    _, env_high = await explain_signal(_signal(), {"symbol": "NG"}, envelope_confidence="high")
    assert env_high.confidence == "high"
    _, env_low = await explain_signal(
        _signal(direction="neutral"), {"symbol": "CL"}, envelope_confidence="low"
    )
    assert env_low.confidence == "low"


async def test_explain_signal_default_is_low_not_medium():
    """No envelope_confidence passed → conservative 'low', never the old hardcoded 'medium'."""
    _, env = await explain_signal(_signal(), {"symbol": "HO"})
    assert env.confidence == "low"


async def test_summarize_market_surfaces_passed_confidence():
    _, env = await summarize_market({"symbol": "NG", "direction": "bullish"},
                                    envelope_confidence="medium")
    assert env.confidence == "medium"
    _, env_default = await summarize_market({"symbol": "GC", "direction": "neutral"})
    assert env_default.confidence == "low"


async def test_generate_thesis_surfaces_passed_confidence():
    _, env = await generate_thesis({"symbol": "NG", "name": "Natural Gas"},
                                   envelope_confidence="high")
    assert env.confidence == "high"
    _, env_default = await generate_thesis({"symbol": "SI", "name": "Silver"})
    assert env_default.confidence == "low"


async def test_end_to_end_derivation_high_agreement_tight_band():
    """derive (high agreement, tight band) → 'high' → surfaces on explain_signal."""
    env_conf = derive_envelope_confidence(ensemble_confidence="high", band_width=0.04)
    assert env_conf == "high"
    _, env = await explain_signal(_signal(), {"symbol": "NG"}, envelope_confidence=env_conf)
    assert env.confidence == "high"


async def test_end_to_end_derivation_high_agreement_wide_band_downgrades():
    """A very wide band floors confidence to 'low' even at high agreement."""
    env_conf = derive_envelope_confidence(ensemble_confidence="high", band_width=0.25)
    assert env_conf == "low"
    _, env = await explain_signal(_signal(), {"symbol": "NG"}, envelope_confidence=env_conf)
    assert env.confidence == "low"


def test_no_hardcoded_confidence_in_forecast_narratives():
    """Regression guard: the three forecast narratives must not re-introduce a literal
    confidence — they take it from the derived `envelope_confidence` (default 'low')."""
    for fn in (explain_signal, summarize_market, generate_thesis):
        src = inspect.getsource(fn)
        assert 'confidence="medium"' not in src, fn.__name__
        assert 'confidence="high"' not in src, fn.__name__
        assert "envelope_confidence" in src, fn.__name__
