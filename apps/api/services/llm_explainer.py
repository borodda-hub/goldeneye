"""
LLM explainer service. All methods return (text: str, envelope: SafetyEnvelope).
Every response goes through scan_for_forbidden; raises SafetyViolation on second failure.
Results are cached in memory (simple dict) keyed by hash of inputs.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime

from apps.api.services.llm_client import call_llm
from apps.api.services.llm_prompts import (
    explain_signal_messages,
    extract_event_messages,
    narrate_scenario_messages,
    review_journal_entry_messages,
    summarize_market_messages,
)
from apps.api.services.safety import (
    DISCLAIMER,
    SafetyEnvelope,
    SafetyViolation,
    scan_for_forbidden,
    wrap_with_uncertainty,
)
from apps.api.src.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory response caches: keyed by hex digest of message content
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[str, SafetyEnvelope]] = {}
_event_cache: dict[str, dict] = {}  # type: ignore[type-arg]


def _cache_key(messages: list[dict]) -> str:  # type: ignore[type-arg]
    """Return a stable hex digest for a list of messages."""
    serialized = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def _call_with_safety_check(
    task: str,
    messages: list[dict],  # type: ignore[type-arg]
    model: str,
    max_tokens: int = 400,
) -> str:
    """
    Call LLM, check forbidden phrases. If first attempt fails, retry once with a stricter
    addendum. Second failure raises SafetyViolation.
    """
    text = await call_llm(task=task, messages=messages, model=model, max_tokens=max_tokens)

    if not scan_for_forbidden(text):
        return text

    # First failure — retry with a stricter prompt addendum
    logger.warning("Safety scan failed on first attempt for task=%r. Retrying with stricter prompt.", task)
    strict_messages = messages + [
        {
            "role": "user",
            "content": (
                "IMPORTANT: Your previous response contained prohibited language. "
                "Rewrite it strictly following the hard rules: do NOT use guaranteed, "
                "will profit, sure thing, risk-free, buy now, sell now, go long, go short, "
                "hot tip, moonshot, or assert any specific future price level. "
                "Always mark inference as inference. Be cautious and institutional in tone."
            ),
        }
    ]
    text = await call_llm(task=task, messages=strict_messages, model=model, max_tokens=max_tokens)

    if scan_for_forbidden(text):
        raise SafetyViolation(
            f"LLM output for task={task!r} contains forbidden phrases after retry. "
            "Response blocked."
        )

    return text


def _select_model(task: str) -> str:
    """Select fast or smart model based on task type."""
    fast_tasks = {"summarize_market", "extract_event"}
    if task in fast_tasks:
        return settings.llm_model_fast
    return settings.llm_model_smart


async def summarize_market(ctx: dict) -> tuple[str, SafetyEnvelope]:  # type: ignore[type-arg]
    """
    Generate a market summary narrative.

    Returns (text, SafetyEnvelope) with confidence="medium".
    """
    messages = summarize_market_messages(ctx)
    key = _cache_key(messages)
    if key in _cache:
        return _cache[key]

    model = _select_model("summarize_market")
    text = await _call_with_safety_check("summarize_market", messages, model=model)

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=[
            "Model outputs are statistical inferences only, not financial advice.",
            "Based on synthetic mock data for research purposes.",
        ],
        as_of=datetime.utcnow(),
    )
    result = (text, envelope)
    _cache[key] = result
    return result


async def explain_signal(signal: dict, ctx: dict) -> tuple[str, SafetyEnvelope]:  # type: ignore[type-arg]
    """
    Generate a signal explanation narrative.

    Returns (text, SafetyEnvelope) with confidence="medium".
    """
    messages = explain_signal_messages(signal, ctx)
    key = _cache_key(messages)
    if key in _cache:
        return _cache[key]

    model = _select_model("explain_signal")
    text = await _call_with_safety_check("explain_signal", messages, model=model)

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=[
            "Model outputs are statistical inferences only, not financial advice.",
            "Based on synthetic mock data for research purposes.",
        ],
        as_of=datetime.utcnow(),
    )
    result = (text, envelope)
    _cache[key] = result
    return result


async def narrate_scenario(
    scenario: dict,  # type: ignore[type-arg]
    results: dict,  # type: ignore[type-arg]
    ctx: dict,  # type: ignore[type-arg]
) -> tuple[str, SafetyEnvelope]:
    """
    Generate a scenario narrative.

    Returns (text, SafetyEnvelope) with confidence="low" (scenario forecasts carry higher uncertainty).
    """
    messages = narrate_scenario_messages(scenario, results, ctx)
    key = _cache_key(messages)
    if key in _cache:
        return _cache[key]

    model = _select_model("narrate_scenario")
    text = await _call_with_safety_check("narrate_scenario", messages, model=model)

    envelope = wrap_with_uncertainty(
        {},
        confidence="low",
        caveats=[
            "Scenario outputs are hypothetical and do not represent forecasts of actual outcomes.",
            "Model outputs are statistical inferences only, not financial advice.",
            "Based on synthetic mock data for research purposes.",
        ],
        as_of=datetime.utcnow(),
    )
    result = (text, envelope)
    _cache[key] = result
    return result


async def review_journal_entry(entry: dict) -> tuple[str, SafetyEnvelope]:  # type: ignore[type-arg]
    """
    Generate a decision-quality review of a journal entry.
    Journal review is NOT cached (per docs/AI_BEHAVIOR.md §caching).

    Returns (text, SafetyEnvelope) with confidence="medium".
    """
    messages = review_journal_entry_messages(entry)

    model = _select_model("review_journal_entry")
    text = await _call_with_safety_check("review_journal_entry", messages, model=model)

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=[
            "This review assesses decision quality only, not the merits of any specific position.",
            "Model outputs are statistical inferences only, not financial advice.",
        ],
        as_of=datetime.utcnow(),
    )
    return (text, envelope)


async def extract_event(article: dict) -> dict:  # type: ignore[type-arg]
    """
    Extract structured event metadata from a news article.

    Returns a dict with keys: category, sentiment, impact_score, affected_regions, entities.
    """
    messages = extract_event_messages(article)
    key = _cache_key(messages)

    if key in _event_cache:
        return _event_cache[key]

    model = _select_model("extract_event")
    text = await call_llm(task="extract_event", messages=messages, model=model)

    # Parse JSON response; fall back to safe default on failure
    result = _parse_event_json(text)
    _event_cache[key] = result
    return result


def _parse_event_json(text: str) -> dict:  # type: ignore[type-arg]
    """Parse JSON from LLM output; return safe default on error."""
    # Strip markdown code fences if present
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first and last fence lines
        inner_lines = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner_lines)

    try:
        data = json.loads(stripped)
        return {
            "category": str(data.get("category", "other")),
            "sentiment": float(data.get("sentiment", 0.0)),
            "impact_score": float(data.get("impact_score", 0.0)),
            "affected_regions": list(data.get("affected_regions", [])),
            "entities": list(data.get("entities", [])),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse extract_event JSON response: %s. Text: %r", exc, text[:200])
        return {
            "category": "other",
            "sentiment": 0.0,
            "impact_score": 0.0,
            "affected_regions": [],
            "entities": [],
        }
