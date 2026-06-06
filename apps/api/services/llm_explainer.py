"""LLM explainer service. All methods return (text: str, envelope: SafetyEnvelope).

Every response goes through scan_for_forbidden; raises SafetyViolation on
second failure. Results are cached in memory keyed by hash of the prompt
text. Model selection routes through `services.llm_routing.select_model`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any

_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _lenient_json_load(text: str) -> Any:
    """json.loads with one fallback that strips trailing commas before }/].
    Some Anthropic responses include them; valid JS, invalid JSON."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return json.loads(_TRAILING_COMMA_RE.sub(r"\1", text))

from apps.api.services.llm_client import call_llm
from apps.api.services.llm_prompts import (
    PromptParts,
    critique_thesis_messages,
    explain_signal_messages,
    extract_event_messages,
    extract_prediction_messages,
    generate_thesis_messages,
    narrate_scenario_messages,
    review_journal_entry_messages,
    summarize_market_messages,
)
from apps.api.services.llm_routing import select_model
from apps.api.services.safety import (
    SafetyEnvelope,
    SafetyViolation,
    scan_for_forbidden,
    wrap_with_uncertainty,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory response caches: keyed by hex digest of prompt content.
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[str, SafetyEnvelope]] = {}
_event_cache: dict[str, dict[str, Any]] = {}
_thesis_cache: dict[str, tuple[dict[str, Any], SafetyEnvelope]] = {}


def _cache_key(prompt: PromptParts) -> str:
    """Return a stable hex digest for a PromptParts object."""
    payload = {
        "system": [b.get("text", "") for b in prompt.system_blocks],
        "user": [m.get("content", "") for m in prompt.user_messages],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def _call_with_safety_check(
    task: str,
    prompt: PromptParts,
    model: str,
    max_tokens: int = 400,
) -> str:
    """Call LLM, check forbidden phrases. Retry once with stricter prompt on first fail."""
    text = await call_llm(task=task, prompt=prompt, model=model, max_tokens=max_tokens)

    if not scan_for_forbidden(text):
        return text

    logger.warning(
        "Safety scan failed on first attempt for task=%r. Retrying with stricter prompt.", task
    )
    strict_user = list(prompt.user_messages) + [
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
    strict_prompt = PromptParts(system_blocks=prompt.system_blocks, user_messages=strict_user)
    text = await call_llm(task=task, prompt=strict_prompt, model=model, max_tokens=max_tokens)

    if scan_for_forbidden(text):
        raise SafetyViolation(
            f"LLM output for task={task!r} contains forbidden phrases after retry. Response blocked."
        )

    return text


async def summarize_market(ctx: dict[str, Any]) -> tuple[str, SafetyEnvelope]:
    prompt = summarize_market_messages(ctx)
    key = _cache_key(prompt)
    if key in _cache:
        return _cache[key]

    model = select_model("summarize_market", ctx)
    text = await _call_with_safety_check("summarize_market", prompt, model=model)

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


async def generate_thesis(
    ctx: dict[str, Any],
) -> tuple[dict[str, Any], SafetyEnvelope]:
    """Synthesize a per-instrument research thesis using current trends + news.

    Returns ({"thesis": str, "drivers": [str], "watch": [str]}, envelope).
    Cached on ctx hash. Degrades to an empty-but-shaped object on malformed
    JSON so the UI can still render with the safety envelope.
    """
    prompt = generate_thesis_messages(ctx)
    key = _cache_key(prompt)
    if key in _thesis_cache:
        return _thesis_cache[key]

    model = select_model("generate_thesis", ctx)
    text = await _call_with_safety_check(
        "generate_thesis", prompt, model=model, max_tokens=600
    )
    parsed = _parse_thesis_json(text)
    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=[
            "Thesis is an LLM inference over current snapshot data, not a forecast.",
            "Based on synthetic mock data for research purposes.",
        ],
        as_of=datetime.utcnow(),
    )
    result = (parsed, envelope)
    _thesis_cache[key] = result
    return result


def _parse_thesis_json(text: str) -> dict[str, Any]:
    """Parse JSON thesis; degrade to empty-but-shaped on failure."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner_lines = (
            lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        )
        stripped = "\n".join(inner_lines)
    try:
        data = _lenient_json_load(stripped)
        return {
            "thesis": str(data.get("thesis", "")).strip(),
            "drivers": [str(s).strip() for s in (data.get("drivers") or [])][:5],
            "watch": [str(s).strip() for s in (data.get("watch") or [])][:4],
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse generate_thesis JSON: %s. Text (first 500 chars): %r",
            exc,
            stripped[:500],
        )
        return {"thesis": "", "drivers": [], "watch": []}


async def explain_signal(
    signal: dict[str, Any], ctx: dict[str, Any]
) -> tuple[str, SafetyEnvelope]:
    prompt = explain_signal_messages(signal, ctx)
    key = _cache_key(prompt)
    if key in _cache:
        return _cache[key]

    model = select_model("explain_signal", {**ctx, **signal})
    text = await _call_with_safety_check("explain_signal", prompt, model=model)

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
    scenario: dict[str, Any],
    results: dict[str, Any],
    ctx: dict[str, Any],
) -> tuple[str, SafetyEnvelope]:
    prompt = narrate_scenario_messages(scenario, results, ctx)
    key = _cache_key(prompt)
    if key in _cache:
        return _cache[key]

    # Escalate to Opus when shocks ≥ 4 (locked rule).
    routing_ctx = {"num_shocks": len(scenario.get("shocks", []) or [])}
    model = select_model("narrate_scenario", routing_ctx)
    text = await _call_with_safety_check("narrate_scenario", prompt, model=model)

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


async def review_journal_entry(entry: dict[str, Any]) -> tuple[str, SafetyEnvelope]:
    """Journal review is NOT cached (per docs/AI_BEHAVIOR.md §caching)."""
    prompt = review_journal_entry_messages(entry)

    # Escalate to Opus when confidence_pct ≥ 80 (locked rule).
    routing_ctx = {"confidence_pct": entry.get("confidence_pct") or 0}
    model = select_model("review_journal_entry", routing_ctx)
    text = await _call_with_safety_check("review_journal_entry", prompt, model=model)

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


async def critique_thesis(
    thesis: dict[str, Any],
) -> tuple[dict[str, list[str]], SafetyEnvelope]:
    """Critique a Working Thesis. Returns (parsed_json, envelope).

    Output is structured as {"missed_risks": [...], "blind_spots": [...],
    "questions": [...]}. If the LLM returns malformed JSON, we degrade to
    empty lists rather than 500'ing — the UI can still render the safety
    envelope.

    Not cached: critique is requested intentionally by the user and the
    expected value is the fresh probe, not the deterministic replay.
    """
    prompt = critique_thesis_messages(thesis)
    routing_ctx = {"conviction_pct": thesis.get("conviction_pct") or 0}
    model = select_model("critique_thesis", routing_ctx)
    text = await _call_with_safety_check("critique_thesis", prompt, model=model)

    parsed = _parse_critique_json(text)
    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=[
            "Critique assesses decision quality only, not the merits of the directional view.",
            "Model outputs are statistical inferences only, not financial advice.",
        ],
        as_of=datetime.utcnow(),
    )
    return (parsed, envelope)


def _parse_critique_json(text: str) -> dict[str, list[str]]:
    """Parse JSON critique; degrade to empty lists on failure."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner_lines = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner_lines)
    try:
        data = _lenient_json_load(stripped)
        return {
            "missed_risks": [str(s) for s in (data.get("missed_risks") or [])][:5],
            "blind_spots": [str(s) for s in (data.get("blind_spots") or [])][:4],
            "questions": [str(s) for s in (data.get("questions") or [])][:4],
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse critique_thesis JSON: %s. Text (first 500 chars): %r",
            exc,
            stripped[:500],
        )
        return {"missed_risks": [], "blind_spots": [], "questions": []}


async def extract_prediction(
    hypothesis: str, instrument: str, current_price: float | None
) -> dict[str, Any]:
    """Distill a prose thesis into a machine-resolvable claim:
    {direction, horizon_days, threshold_pct, rationale}. The output is structured
    fields (not prose), so it skips the forbidden-phrase gate. Degrades to a safe
    neutral default on malformed JSON so the UI can always render a proposal.
    """
    prompt = extract_prediction_messages(hypothesis, instrument, current_price)
    model = select_model("extract_prediction", {})
    text = await call_llm(task="extract_prediction", prompt=prompt, model=model)
    return _parse_prediction_json(text)


def _parse_prediction_json(text: str) -> dict[str, Any]:
    """Parse + clamp the prediction JSON; safe neutral default on failure."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner)
    try:
        data = _lenient_json_load(stripped)
        direction = str(data.get("direction", "neutral")).lower()
        if direction not in {"bullish", "bearish", "neutral"}:
            direction = "neutral"
        horizon = max(1, min(int(data.get("horizon_days") or 14), 90))
        threshold = max(0.1, min(float(data.get("threshold_pct") or 2.0), 50.0))
        return {
            "direction": direction,
            "horizon_days": horizon,
            "threshold_pct": round(threshold, 2),
            "rationale": str(data.get("rationale", "")).strip()[:200],
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse extract_prediction JSON: %s. Text: %r", exc, text[:200]
        )
        return {
            "direction": "neutral",
            "horizon_days": 14,
            "threshold_pct": 2.0,
            "rationale": "",
        }


async def extract_event(article: dict[str, Any]) -> dict[str, Any]:
    prompt = extract_event_messages(article)
    key = _cache_key(prompt)
    if key in _event_cache:
        return _event_cache[key]

    model = select_model("extract_event", article)
    text = await call_llm(task="extract_event", prompt=prompt, model=model)
    result = _parse_event_json(text)
    _event_cache[key] = result
    return result


def _parse_event_json(text: str) -> dict[str, Any]:
    """Parse JSON from LLM output; return safe default on error."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
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
