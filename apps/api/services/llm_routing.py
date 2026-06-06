"""Per-task LLM model routing.

The matrix (locked in docs/PHASE_09_PLAN.md §1.5a):

    summarize_market       → Haiku    (one-liner, high frequency)
    extract_event          → Haiku    (structured JSON, no creative reasoning)
    explain_signal         → Sonnet   (multi-input reasoning, safety-critical prose)
    narrate_scenario       → Sonnet   (5 required sections; Opus when shocks ≥ 4)
    review_journal_entry   → Sonnet   (Opus when confidence_pct ≥ 80)

Env overrides via `LLM_MODEL_<TASK_UPPER>` settings fields force a specific
model for a task — used for testing and for cost-cap downgrades.
"""
from __future__ import annotations

from typing import Any

from apps.api.src.settings import settings

# Tasks that default to the fast model.
_FAST_TASKS: frozenset[str] = frozenset(
    {"summarize_market", "extract_event", "extract_prediction"}
)

# Thresholds for escalating to the premium model.
_NARRATE_SCENARIO_OPUS_MIN_SHOCKS: int = 4
_REVIEW_JOURNAL_OPUS_MIN_CONFIDENCE_PCT: float = 80.0
_CRITIQUE_THESIS_OPUS_MIN_CONVICTION_PCT: float = 80.0


def _override_for(task: str) -> str:
    """Read a per-task env override, if set."""
    attr = f"llm_model_{task}"
    value = getattr(settings, attr, "")
    return value if isinstance(value, str) and value else ""


def select_model(task: str, ctx: dict[str, Any] | None = None) -> str:
    """Return the model ID to use for `task` given `ctx`.

    Args:
        task: One of "summarize_market" | "explain_signal" |
              "narrate_scenario" | "review_journal_entry" | "extract_event".
        ctx: Optional context the caller passes for escalation decisions.
             Recognized keys:
                - num_shocks: int — used by narrate_scenario
                - confidence_pct: float — used by review_journal_entry

    Returns:
        A model ID string. Per-task env overrides take precedence; otherwise
        the routing matrix applies.
    """
    override = _override_for(task)
    if override:
        return override

    if task in _FAST_TASKS:
        return settings.llm_model_fast

    ctx = ctx or {}

    if task == "narrate_scenario":
        num_shocks = int(ctx.get("num_shocks", 0))
        if num_shocks >= _NARRATE_SCENARIO_OPUS_MIN_SHOCKS:
            return settings.llm_model_premium

    if task == "review_journal_entry":
        confidence_pct = float(ctx.get("confidence_pct") or 0.0)
        if confidence_pct >= _REVIEW_JOURNAL_OPUS_MIN_CONFIDENCE_PCT:
            return settings.llm_model_premium

    if task in ("critique_thesis", "devils_advocate"):
        conviction_pct = float(ctx.get("conviction_pct") or 0.0)
        if conviction_pct >= _CRITIQUE_THESIS_OPUS_MIN_CONVICTION_PCT:
            return settings.llm_model_premium

    return settings.llm_model_smart
