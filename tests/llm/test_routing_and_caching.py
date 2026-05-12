"""Tests for per-task LLM model routing + prompt-caching restructure (Phase 09 §1.5a-c)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.llm_prompts import (
    PERSONA_PROMPT,
    PromptParts,
    explain_signal_messages,
    extract_event_messages,
    narrate_scenario_messages,
    review_journal_entry_messages,
    summarize_market_messages,
)
from apps.api.services.llm_routing import select_model


# ──────────────────────────────────────────────────────────────────────────
# Routing matrix (locked rules from docs/PHASE_09_PLAN.md §1.5a)
# ──────────────────────────────────────────────────────────────────────────


def test_summarize_market_routes_to_fast(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_summarize_market", "")
    assert select_model("summarize_market") == s.settings.llm_model_fast


def test_extract_event_routes_to_fast(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_extract_event", "")
    assert select_model("extract_event") == s.settings.llm_model_fast


def test_explain_signal_routes_to_smart(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_explain_signal", "")
    assert select_model("explain_signal") == s.settings.llm_model_smart


def test_narrate_scenario_default_is_smart(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_narrate_scenario", "")
    assert select_model("narrate_scenario", {"num_shocks": 1}) == s.settings.llm_model_smart
    assert select_model("narrate_scenario", {"num_shocks": 3}) == s.settings.llm_model_smart


def test_narrate_scenario_escalates_to_premium_at_4_shocks(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_narrate_scenario", "")
    assert select_model("narrate_scenario", {"num_shocks": 4}) == s.settings.llm_model_premium
    assert select_model("narrate_scenario", {"num_shocks": 10}) == s.settings.llm_model_premium


def test_review_journal_entry_default_is_smart(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_review_journal_entry", "")
    assert select_model("review_journal_entry", {"confidence_pct": 0}) == s.settings.llm_model_smart
    assert select_model("review_journal_entry", {"confidence_pct": 60}) == s.settings.llm_model_smart
    assert select_model("review_journal_entry", {"confidence_pct": 79}) == s.settings.llm_model_smart


def test_review_journal_entry_escalates_at_80_confidence(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_review_journal_entry", "")
    assert select_model("review_journal_entry", {"confidence_pct": 80}) == s.settings.llm_model_premium
    assert select_model("review_journal_entry", {"confidence_pct": 95}) == s.settings.llm_model_premium


def test_env_override_wins_over_routing(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_summarize_market", "claude-overridden-test")
    assert select_model("summarize_market") == "claude-overridden-test"


def test_env_override_wins_even_over_escalation(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_review_journal_entry", "claude-forced-haiku")
    assert select_model("review_journal_entry", {"confidence_pct": 95}) == "claude-forced-haiku"


def test_review_journal_entry_handles_missing_confidence(monkeypatch):
    from apps.api.src import settings as s
    monkeypatch.setattr(s.settings, "llm_model_review_journal_entry", "")
    assert select_model("review_journal_entry", {}) == s.settings.llm_model_smart
    assert select_model("review_journal_entry", None) == s.settings.llm_model_smart


# ──────────────────────────────────────────────────────────────────────────
# Prompt caching structure — persona block must be marked cacheable
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "builder,args",
    [
        (summarize_market_messages, ({},)),
        (explain_signal_messages, ({"direction": "bullish"}, {})),
        (narrate_scenario_messages, ({"name": "X", "shocks": []}, {}, {})),
        (review_journal_entry_messages, ({"hypothesis": "test"},)),
        (extract_event_messages, ({"title": "X"},)),
    ],
)
def test_all_builders_return_prompt_parts_with_cacheable_persona(builder, args):
    parts = builder(*args)
    assert isinstance(parts, PromptParts)
    assert len(parts.system_blocks) >= 2
    persona = parts.system_blocks[0]
    assert persona["type"] == "text"
    assert persona["text"] == PERSONA_PROMPT
    assert persona["cache_control"] == {"type": "ephemeral"}


def test_task_instructions_block_is_not_cached():
    """Only the persona block carries cache_control; per-task headers do not."""
    parts = summarize_market_messages({})
    task_block = parts.system_blocks[1]
    assert task_block["type"] == "text"
    assert "cache_control" not in task_block
    assert "summarize_market" in task_block["text"]


def test_persona_block_is_byte_identical_across_methods():
    """Cache hits only happen if the cached prefix is exactly the same — verify."""
    summary = summarize_market_messages({}).system_blocks[0]
    explain = explain_signal_messages({"direction": "bullish"}, {}).system_blocks[0]
    scenario = narrate_scenario_messages({"name": "x", "shocks": []}, {}, {}).system_blocks[0]
    review = review_journal_entry_messages({"hypothesis": "x"}).system_blocks[0]
    extract = extract_event_messages({"title": "x"}).system_blocks[0]
    assert summary == explain == scenario == review == extract


# ──────────────────────────────────────────────────────────────────────────
# Context trimming (locked in §1.5c)
# ──────────────────────────────────────────────────────────────────────────


def test_explain_signal_caps_supporting_and_contradicting_to_top_2():
    signal = {
        "direction": "bullish",
        "models": [
            {
                "model_name": "test_model",
                "direction": "bullish",
                "supporting": [
                    {"factor": "F1", "weight": 0.9},
                    {"factor": "F2", "weight": 0.8},
                    {"factor": "F3-should-be-omitted", "weight": 0.7},
                    {"factor": "F4-should-be-omitted", "weight": 0.6},
                ],
                "contradicting": [
                    {"factor": "C1", "weight": 0.5},
                    {"factor": "C2", "weight": 0.4},
                    {"factor": "C3-should-be-omitted", "weight": 0.3},
                ],
            }
        ],
    }
    parts = explain_signal_messages(signal, {})
    user_text = parts.user_messages[0]["content"]
    assert "F1" in user_text and "F2" in user_text
    assert "F3-should-be-omitted" not in user_text
    assert "F4-should-be-omitted" not in user_text
    assert "C1" in user_text and "C2" in user_text
    assert "C3-should-be-omitted" not in user_text


def test_review_journal_entry_caps_evidence_to_first_5():
    entry = {
        "hypothesis": "test",
        "evidence": [f"E{i}" for i in range(8)],
        "confidence_pct": 50,
    }
    parts = review_journal_entry_messages(entry)
    user_text = parts.user_messages[0]["content"]
    for kept in range(5):
        assert f"E{kept}" in user_text
    for dropped in range(5, 8):
        assert f"E{dropped}" not in user_text
    assert "omitted" in user_text


def test_summarize_market_caps_top_events_to_3():
    """Top-3 events only; older entries dropped."""
    ctx = {"top_events": ["e1", "e2", "e3", "e4-should-be-omitted", "e5-should-be-omitted"]}
    parts = summarize_market_messages(ctx)
    user_text = parts.user_messages[0]["content"]
    assert "e1" in user_text and "e2" in user_text and "e3" in user_text
    assert "e4-should-be-omitted" not in user_text


# ──────────────────────────────────────────────────────────────────────────
# call_llm uses system + cache_control on real-mode API calls
# ──────────────────────────────────────────────────────────────────────────


def test_call_llm_passes_system_blocks_and_user_messages_separately(monkeypatch):
    """In real mode, persona block goes via the `system` arg, not the user message."""
    from apps.api.src import settings as s
    from apps.api.services import llm_client

    monkeypatch.setattr(s.settings, "llm_mode", "real")
    monkeypatch.setattr(s.settings, "anthropic_api_key", "test-key")

    parts = summarize_market_messages({"price": 3.4, "vol_regime": "normal"})

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ok")]

    async def fake_create(**kwargs):
        assert "system" in kwargs, "real-mode call must pass `system` param for caching"
        assert kwargs["system"] == parts.system_blocks
        assert kwargs["messages"] == parts.user_messages
        # Cache control must be on the persona block specifically.
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
        return fake_response

    fake_messages = MagicMock()
    fake_messages.create = fake_create
    fake_client = MagicMock()
    fake_client.messages = fake_messages

    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        result = asyncio.run(
            llm_client.call_llm(task="summarize_market", prompt=parts, model="test-model")
        )
    assert result == "ok"


def test_call_llm_falls_back_to_canned_on_error(monkeypatch):
    from apps.api.src import settings as s
    from apps.api.services import llm_client

    monkeypatch.setattr(s.settings, "llm_mode", "real")
    monkeypatch.setattr(s.settings, "anthropic_api_key", "test-key")

    parts = summarize_market_messages({})

    async def explode(**kwargs):
        raise RuntimeError("api went boom")

    fake_messages = MagicMock()
    fake_messages.create = explode
    fake_client = MagicMock()
    fake_client.messages = fake_messages

    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        result = asyncio.run(
            llm_client.call_llm(task="summarize_market", prompt=parts, model="test-model")
        )
    # Canned fallback is non-empty and contains an inference marker.
    assert "appear" in result.lower() or "suggests" in result.lower() or "reads as" in result.lower()
