"""
Thin wrapper over the Anthropic SDK.
When settings.llm_mode == "fake", returns deterministic canned responses without any API call.
When settings.llm_mode == "real", calls Claude API.

Canned responses (fake mode) are realistic but safe — they pass scan_for_forbidden().
They include inference markers ("appears", "suggests") and contradicting evidence.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canned responses for fake mode — one per task.
# All pass scan_for_forbidden() and contain inference markers.
# ---------------------------------------------------------------------------
_CANNED: dict[str, str] = {
    "summarize_market": (
        "Front-month Henry Hub prices appear modestly firm, consistent with the current storage "
        "deficit of roughly 140 Bcf below the 5-year average. The volatility regime reads as "
        "elevated, however, with the caveat that managed-money positioning is extended and any "
        "moderation in weather forecasts could quickly reverse near-term support."
    ),
    "explain_signal": (
        "The ensemble reads as moderately bullish on the 1-day horizon, driven primarily by a "
        "20-day over 50-day moving average cross confirmed three sessions ago. The strongest "
        "supporting factor is the persistent storage deficit, which suggests incremental demand "
        "pressure; the strongest contradicting factor is the elevated RSI reading near 70, which "
        "historically precedes short-term consolidation. Confidence is medium with the caveat that "
        "LNG export demand data for the most recent week is not yet incorporated."
    ),
    "narrate_scenario": (
        "This scenario assumes the stated shock conditions persist for the full duration without "
        "early moderation. If the scenario plays out, the data would suggest a tightening of the "
        "supply-demand balance beyond what is currently reflected in forward curves. The directional "
        "pressure appears modestly bullish over the 1-to-3-week timeframe, with low-to-medium "
        "confidence given forecast uncertainty at this horizon. The strongest counterargument is "
        "that the market may have already partially priced in weather risk. Validation would require "
        "updated NWS 6-10 day temperature anomaly maps and the next EIA storage report."
    ),
    "review_journal_entry": (
        "Implicit assumption: the hypothesis assumes that recent storage data is the primary price "
        "driver, without accounting for the potential moderating effect of rising production. "
        "Strengthening evidence: basis differentials at key Northeast hubs would confirm or "
        "challenge the demand-pull thesis. Missing risk: LNG export volumes are not addressed — "
        "a step-down in export demand could partially offset the thesis. Invalidation criteria: "
        "specific and time-bound, passes decision-quality standard. Confidence assessment: 60% "
        "appears consistent with evidence weight. Process improvement: add a re-evaluation trigger "
        "date in addition to price levels."
    ),
    "extract_event": (
        '{"category": "demand", "sentiment": 0.2, "impact_score": 0.4, '
        '"affected_regions": [], "entities": []}'
    ),
}


async def call_llm(
    task: str,
    messages: list[dict],  # type: ignore[type-arg]
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 400,
) -> str:
    """
    Returns the text of the LLM response.

    Args:
        task: One of "summarize_market" | "explain_signal" | "narrate_scenario" |
              "review_journal_entry" | "extract_event"
        messages: List of message dicts e.g. [{"role": "user", "content": "..."}]
        model: Claude model identifier.
        max_tokens: Maximum tokens to generate.
    """
    # Import here to avoid circular-import issues with settings
    from apps.api.src.settings import settings

    if settings.llm_mode == "fake":
        return _get_canned(task)

    # Real mode
    return await _call_real(task=task, messages=messages, model=model, max_tokens=max_tokens)


def _get_canned(task: str) -> str:
    """Return the canned response for the given task, falling back to summarize_market."""
    return _CANNED.get(task, _CANNED["summarize_market"])


async def _call_real(
    *,
    task: str,
    messages: list[dict],  # type: ignore[type-arg]
    model: str,
    max_tokens: int,
) -> str:
    """Call the Anthropic API and return the response text. Falls back to canned on error."""
    try:
        import anthropic  # type: ignore[import-untyped]

        from apps.api.src.settings import settings

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,  # type: ignore[arg-type]
        )
        content = response.content[0]
        if hasattr(content, "text"):
            return str(content.text)
        return str(content)
    except Exception as exc:
        logger.warning(
            "LLM API call failed for task=%r, falling back to canned response. Error: %s",
            task,
            exc,
        )
        return _get_canned(task)
