"""LLM prompt builder functions.

Implements the 5 prompt builders from docs/AI_BEHAVIOR.md §prompt_templates.
Each builder returns a `PromptParts` (system_blocks, user_messages) so the
persona/rules block can be cached at the API level (~90% input-token
reduction on repeat calls).

Cache layout per call:
    system: [PERSONA + HARD_RULES]   ← cached (ephemeral, 5-min TTL)
    system: [task-specific instructions]
    user:   [dynamic ctx]            ← not cached
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Cacheable persona + hard-rules block. Identical across all 5 methods.
# (Exact text from docs/AI_BEHAVIOR.md §prompt_templates §shared_system_prompt.)
# ---------------------------------------------------------------------------
PERSONA_PROMPT: str = (
    "You are the Goldeneye desk analyst. You write short, institutional, cautious commodity research "
    "notes for an internal team.\n\n"
    "Hard rules:\n"
    "- You do not give personalized financial advice.\n"
    "- You never use the words: guaranteed, will profit, sure thing, risk-free, buy now, sell now, "
    "go long, go short, hot tip, moonshot, recommend.\n"
    "- You always mark inference as inference (\"appears\", \"suggests\", \"reads as\").\n"
    "- You always include at least one contradicting consideration when you express a directional view.\n"
    "- You always state a confidence band that matches the data: low / moderate / high.\n"
    "- You never assert a specific future price level. Ranges are acceptable; point predictions are not.\n\n"
    "Output is read by analysts who have already seen the underlying data. Be concise."
)

# Backwards-compatibility alias for tests still importing SYSTEM_PROMPT directly.
SYSTEM_PROMPT: str = PERSONA_PROMPT

# Context-trimming caps (locked in docs/PHASE_09_PLAN.md §1.5c).
_EXPLAIN_SIGNAL_TOP_FACTORS = 2
_REVIEW_JOURNAL_TOP_EVIDENCE = 5
_EXTRACT_EVENT_BODY_CHARS = 800


@dataclass(frozen=True)
class PromptParts:
    """Structured prompt — system blocks (cacheable) + user messages (dynamic)."""

    system_blocks: list[dict[str, Any]]
    user_messages: list[dict[str, Any]]

    def to_legacy_messages(self) -> list[dict[str, Any]]:
        """Flatten into the legacy single-message format (system inlined into user).

        Used by the fake LLM path and by older tests that still inspect messages
        as a flat list.
        """
        if not self.user_messages:
            return []
        first = self.user_messages[0]
        system_text = "\n\n".join(
            b.get("text", "") for b in self.system_blocks if b.get("type") == "text"
        )
        combined_content = (
            f"{system_text}\n\n{first.get('content', '')}" if system_text else first.get("content", "")
        )
        return [{"role": first.get("role", "user"), "content": combined_content}, *self.user_messages[1:]]


def _persona_block() -> dict[str, Any]:
    """Persona/rules block with cache_control. Identical across methods."""
    return {
        "type": "text",
        "text": PERSONA_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }


def _task_block(task_instructions: str) -> dict[str, Any]:
    """Per-task instructions block. Not cached (varies in length but always small)."""
    return {"type": "text", "text": task_instructions}


def summarize_market_messages(ctx: dict) -> PromptParts:  # type: ignore[type-arg]
    """Build messages for summarize_market.

    Recognized ctx keys: price, intraday_change, vol_regime, storage_delta,
    storage_vs_5y, cot_mm_change, top_events (list), temp_anomaly. Additional
    keys are ignored (caller can pass a fuller dict without inflating tokens).
    """
    price = ctx.get("price", ctx.get("last_price", "N/A"))
    intraday_change = ctx.get("intraday_change", "N/A")
    vol_regime = ctx.get("vol_regime", "unknown")
    storage_delta = ctx.get("storage_delta", "N/A")
    storage_vs_5y = ctx.get("storage_vs_5y", "N/A")
    cot_mm_change = ctx.get("cot_mm_change", "N/A")
    top_events = ctx.get("top_events", [])
    temp_anomaly = ctx.get("temp_anomaly", "N/A")

    events_text = "\n".join(f"  - {e}" for e in top_events[:3]) if top_events else "  - None available"

    task_instructions = (
        "Task: summarize_market. Write 2-3 sentences. Lead with the most informative data point. "
        "Mark inference. Include one caveat."
    )
    user_content = (
        "Inputs:\n"
        f"- Front-month price: {price}, intraday change: {intraday_change}\n"
        f"- Volatility regime: {vol_regime}\n"
        f"- Storage delta vs consensus: {storage_delta} Bcf; vs 5-year average: {storage_vs_5y} Bcf\n"
        f"- COT managed-money net WoW change: {cot_mm_change}\n"
        f"- Top events (last 5 days):\n{events_text}\n"
        f"- 14-day HDD-weighted temperature anomaly: {temp_anomaly} °F"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )


def explain_signal_messages(signal: dict, ctx: dict) -> PromptParts:  # type: ignore[type-arg]
    """Build messages for explain_signal. Caps supporting/contradicting to top-2 per model."""
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", "low")
    models = signal.get("models", [])
    vol_regime = signal.get("vol_regime", "unknown")
    agreement = signal.get("agreement", {})
    confidence_rationale = signal.get("confidence_rationale", [])
    storage = ctx.get("storage")
    cot = ctx.get("cot")

    models_text_parts: list[str] = []
    for m in models:
        name = m.get("model_name", m.get("name", "unknown"))
        dir_ = m.get("direction", "neutral")
        supporting = (m.get("supporting") or [])[:_EXPLAIN_SIGNAL_TOP_FACTORS]
        contradicting = (m.get("contradicting") or [])[:_EXPLAIN_SIGNAL_TOP_FACTORS]
        sup_str = "; ".join(f.get("factor", "") for f in supporting) if supporting else "none"
        con_str = "; ".join(f.get("factor", "") for f in contradicting) if contradicting else "none"
        models_text_parts.append(
            f"  - {name}: {dir_} | supporting: {sup_str} | contradicting: {con_str}"
        )
    models_text = "\n".join(models_text_parts) if models_text_parts else "  - No model detail available"

    agreement_text = (
        f"{agreement.get('bullish', 0)} bullish, "
        f"{agreement.get('bearish', 0)} bearish, "
        f"{agreement.get('neutral', 0)} neutral of {agreement.get('total', 0)} models"
        if agreement
        else "N/A"
    )
    rationale_text = "; ".join(confidence_rationale) if confidence_rationale else "N/A"

    storage_text = (
        f"EIA storage delta vs consensus: {storage.get('delta_vs_consensus', 'N/A')} Bcf"
        if storage
        else "N/A"
    )
    cot_text = (
        f"Managed-money net WoW delta: {cot.get('mm_net_delta', 'N/A')} contracts"
        if cot
        else "N/A"
    )

    task_instructions = (
        "Task: explain_signal. Write 3-5 sentences. First sentence states the ensemble view. "
        "Following sentences walk through the strongest supporting factor and the strongest "
        "contradicting factor. Conclude with the confidence band and one caveat about what "
        "could invalidate."
    )
    user_content = (
        "Inputs:\n"
        f"- Ensemble direction: {direction}, confidence: {confidence}\n"
        f"- Model agreement: {agreement_text}\n"
        f"- Confidence rationale: {rationale_text}\n"
        f"- Per-model results (top-{_EXPLAIN_SIGNAL_TOP_FACTORS} factors each):\n{models_text}\n"
        f"- Volatility regime: {vol_regime}\n"
        f"- Alt-data context: storage={storage_text}; COT={cot_text}"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )


def narrate_scenario_messages(
    scenario: dict, results: dict, ctx: dict  # type: ignore[type-arg]
) -> PromptParts:
    """Build messages for narrate_scenario."""
    name = scenario.get("name", "Unnamed scenario")
    shocks = scenario.get("shocks", [])
    baseline = results.get("baseline", {})
    shocked = results.get("shocked", {})
    delta_direction = results.get("delta_direction", "unchanged")
    delta_range = results.get("delta_range", {})

    shocks_text = (
        "\n".join(f"  - type={s.get('type', '?')}, {s}" for s in shocks) if shocks else "  - None"
    )

    task_instructions = (
        "Task: narrate_scenario. Output a structured narrative with these sections, each 1-3 sentences:\n"
        "1. What the scenario assumes\n"
        "2. How the data would shift if the scenario plays out\n"
        "3. The directional pressure and confidence band, with the timeframe\n"
        "4. The strongest counterargument\n"
        "5. What data would validate or invalidate this scenario in the next 1-2 weeks\n"
        "Do not add any other sections."
    )
    user_content = (
        f"Scenario name: {name}\n"
        f"Shocks:\n{shocks_text}\n\n"
        f"Baseline forecast: direction={baseline.get('direction', 'N/A')}, "
        f"confidence={baseline.get('confidence', 'N/A')}, "
        f"expected_pct={baseline.get('expected_pct', 'N/A')}\n"
        f"Shocked forecast: direction={shocked.get('direction', 'N/A')}, "
        f"confidence={shocked.get('confidence', 'N/A')}, "
        f"expected_pct={shocked.get('expected_pct', 'N/A')}\n"
        f"Delta in directional pressure: {delta_direction}\n"
        f"Delta in expected range: {delta_range}"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )


def review_journal_entry_messages(entry: dict) -> PromptParts:  # type: ignore[type-arg]
    """Build messages for review_journal_entry. Caps evidence to first 5 rows."""
    hypothesis = entry.get("hypothesis", "N/A")
    evidence = entry.get("evidence", "N/A")
    confidence_pct = entry.get("confidence_pct", "N/A")
    planned_action = entry.get("planned_action", "N/A")
    risk_factors = entry.get("risk_factors", "N/A")
    invalidation_criteria = entry.get("invalidation_criteria", "N/A")

    if isinstance(evidence, list):
        evidence_capped = evidence[:_REVIEW_JOURNAL_TOP_EVIDENCE]
        evidence_str = "; ".join(str(e) for e in evidence_capped)
        if len(evidence) > _REVIEW_JOURNAL_TOP_EVIDENCE:
            evidence_str += f" (+{len(evidence) - _REVIEW_JOURNAL_TOP_EVIDENCE} more, omitted)"
    else:
        evidence_str = str(evidence)
    if isinstance(risk_factors, list):
        risk_factors = "; ".join(str(r) for r in risk_factors)

    task_instructions = (
        "Task: review_journal_entry. Review for decision quality, not endorsing the trade. "
        "Identify, in 4-6 short bullets:\n"
        "- one assumption that is implicit but not stated\n"
        "- one piece of evidence that would strengthen or weaken the hypothesis\n"
        "- one risk factor that is missing or underweighted\n"
        "- whether the invalidation criteria is testable and time-bound\n"
        "- whether the confidence_pct is consistent with the evidence weight\n"
        "- one process improvement for the next entry\n"
        "Do not say whether the trade is a good idea. Do not give a directional view."
    )
    user_content = (
        "Decision Journal Entry:\n"
        f"- Hypothesis: {hypothesis}\n"
        f"- Evidence: {evidence_str}\n"
        f"- Confidence: {confidence_pct}%\n"
        f"- Planned action: {planned_action}\n"
        f"- Risk factors: {risk_factors}\n"
        f"- Invalidation criteria: {invalidation_criteria}"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )


def critique_thesis_messages(thesis: dict) -> PromptParts:  # type: ignore[type-arg]
    """Build messages for critique_thesis.

    The model is asked to push back on the user's view — surfacing
    blind spots, risks the thesis underweights, and clarifying
    questions — without endorsing the directional call. Returns
    JSON with three string-list fields. Output schema is fixed so the
    frontend can render without ad-hoc parsing.
    """
    statement = thesis.get("statement", "")
    supporting = thesis.get("supporting_evidence") or []
    contradicting = thesis.get("contradicting_evidence") or []
    missing_data = thesis.get("missing_data") or []
    conviction_pct = thesis.get("conviction_pct", "N/A")

    def _factors(items: list[dict]) -> str:
        capped = items[:5]
        parts = []
        for it in capped:
            factor = str(it.get("factor", "")).strip()
            note = str(it.get("note", "")).strip()
            if note:
                parts.append(f"{factor} — {note}")
            else:
                parts.append(factor)
        return "; ".join(p for p in parts if p) or "none"

    supporting_text = _factors(supporting)
    contradicting_text = _factors(contradicting)
    missing_text = "; ".join(missing_data[:5]) if missing_data else "none"

    task_instructions = (
        "Task: critique_thesis. Push back on this thesis to test its decision quality. "
        "Identify what the analyst may be missing. Do not say whether the thesis is right "
        "or wrong. Return ONLY a valid JSON object with no markdown fences or commentary, "
        "matching this exact schema:\n"
        '{\n'
        '  "missed_risks": [<3-5 short strings: risks the thesis underweights>],\n'
        '  "blind_spots": [<2-4 short strings: assumptions worth examining>],\n'
        '  "questions": [<2-4 short strings: clarifying questions the analyst should answer>]\n'
        '}\n'
        "Each string ≤ 140 chars. Be specific to the inputs; do not produce generic boilerplate."
    )
    user_content = (
        "Thesis under review:\n"
        f'- Statement: "{statement}"\n'
        f"- Conviction: {conviction_pct}%\n"
        f"- Supporting evidence: {supporting_text}\n"
        f"- Contradicting evidence: {contradicting_text}\n"
        f"- Data analyst still needs: {missing_text}"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )


def extract_event_messages(article: dict) -> PromptParts:  # type: ignore[type-arg]
    """Build messages for extract_event."""
    title = article.get("title", "N/A")
    body = article.get("body", "")
    source = article.get("source", "unknown")
    published_at = article.get("published_at", "unknown")

    body_snippet = body[:_EXTRACT_EVENT_BODY_CHARS] + (
        "..." if len(body) > _EXTRACT_EVENT_BODY_CHARS else ""
    )

    task_instructions = (
        "Task: extract_event. Extract the following fields and return ONLY a valid JSON object "
        "with no additional text:\n"
        '{\n'
        '  "category": "<supply|demand|weather|geopolitical|regulatory|other>",\n'
        '  "sentiment": <float -1.0 to 1.0>,\n'
        '  "impact_score": <float 0.0 to 1.0>,\n'
        '  "affected_regions": [<list of region strings>],\n'
        '  "entities": [<list of entity name strings>]\n'
        '}'
    )
    user_content = (
        "Article:\n"
        f"- Title: {title}\n"
        f"- Source: {source}\n"
        f"- Published: {published_at}\n"
        f"- Body (excerpt): {body_snippet}"
    )

    return PromptParts(
        system_blocks=[_persona_block(), _task_block(task_instructions)],
        user_messages=[{"role": "user", "content": user_content}],
    )
