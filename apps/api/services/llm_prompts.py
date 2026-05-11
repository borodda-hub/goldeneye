"""
LLM prompt builder functions.

Implements the 5 prompt builders from docs/AI_BEHAVIOR.md §prompt_templates.
Each function returns messages: list[dict] ready to pass to call_llm().
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared system prompt — exactly from docs/AI_BEHAVIOR.md §prompt_templates §shared_system_prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT: str = (
    "You are the NGTI desk analyst. You write short, institutional, cautious commodity research "
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


def summarize_market_messages(ctx: dict) -> list[dict]:  # type: ignore[type-arg]
    """
    Build messages for the summarize_market task.

    ctx keys (all optional, use sensible defaults if absent):
        price: float            Front-month price
        intraday_change: float  Intraday price change
        vol_regime: str         Volatility regime
        storage_delta: float    Delta vs consensus (Bcf)
        storage_vs_5y: float    Delta vs 5-year average (Bcf)
        cot_mm_change: float    Week-over-week managed-money net change
        top_events: list[str]   Top 3 events of last 5 days
        temp_anomaly: float     14-day HDD-weighted national temperature anomaly (°F)
    """
    price = ctx.get("price", "N/A")
    intraday_change = ctx.get("intraday_change", "N/A")
    vol_regime = ctx.get("vol_regime", "unknown")
    storage_delta = ctx.get("storage_delta", "N/A")
    storage_vs_5y = ctx.get("storage_vs_5y", "N/A")
    cot_mm_change = ctx.get("cot_mm_change", "N/A")
    top_events = ctx.get("top_events", [])
    temp_anomaly = ctx.get("temp_anomaly", "N/A")

    events_text = "\n".join(f"  - {e}" for e in top_events) if top_events else "  - None available"

    user_content = (
        "Task: summarize_market\n\n"
        "Inputs:\n"
        f"- Front-month price: {price}, intraday change: {intraday_change}\n"
        f"- Volatility regime: {vol_regime}\n"
        f"- Storage delta vs consensus: {storage_delta} Bcf; vs 5-year average: {storage_vs_5y} Bcf\n"
        f"- COT managed-money net WoW change: {cot_mm_change}\n"
        f"- Top events (last 5 days):\n{events_text}\n"
        f"- 14-day HDD-weighted temperature anomaly: {temp_anomaly} °F\n\n"
        "Write 2-3 sentences. Lead with the most informative data point. Mark inference. "
        "Include one caveat."
    )

    return [
        {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_content}"},
    ]


def explain_signal_messages(signal: dict, ctx: dict) -> list[dict]:  # type: ignore[type-arg]
    """
    Build messages for the explain_signal task.

    signal keys:
        direction: str       Ensemble direction (bullish/bearish/neutral)
        confidence: str      Ensemble confidence (low/medium/high)
        models: list[dict]   Per-model results with direction, supporting, contradicting
        vol_regime: str      Volatility regime

    ctx keys:
        cot_crowdedness: float   Crowdedness score from COT (0-1)
    """
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", "low")
    models = signal.get("models", [])
    vol_regime = signal.get("vol_regime", "unknown")
    cot_crowdedness = ctx.get("cot_crowdedness", "N/A")

    models_text_parts: list[str] = []
    for m in models:
        name = m.get("model_name", "unknown")
        dir_ = m.get("direction", "neutral")
        supporting = m.get("supporting", [])
        contradicting = m.get("contradicting", [])
        sup_str = "; ".join(f["factor"] for f in supporting) if supporting else "none"
        con_str = "; ".join(f["factor"] for f in contradicting) if contradicting else "none"
        models_text_parts.append(
            f"  - {name}: {dir_} | supporting: {sup_str} | contradicting: {con_str}"
        )
    models_text = "\n".join(models_text_parts) if models_text_parts else "  - No model detail available"

    user_content = (
        "Task: explain_signal\n\n"
        "Inputs:\n"
        f"- Ensemble direction: {direction}, confidence: {confidence}\n"
        f"- Per-model results:\n{models_text}\n"
        f"- Volatility regime: {vol_regime}\n"
        f"- COT crowdedness score: {cot_crowdedness}\n\n"
        "Write 3-5 sentences. First sentence states the ensemble view. Following sentences walk "
        "through the strongest supporting factor and the strongest contradicting factor. Conclude "
        "with the confidence band and one caveat about what could invalidate."
    )

    return [
        {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_content}"},
    ]


def narrate_scenario_messages(scenario: dict, results: dict, ctx: dict) -> list[dict]:  # type: ignore[type-arg]
    """
    Build messages for the narrate_scenario task.

    scenario keys:
        name: str            Scenario name
        shocks: list[dict]   List of shock dicts

    results keys:
        baseline: dict       Baseline ensemble result
        shocked: dict        Shocked ensemble result
        delta_direction: str Change in directional pressure
        delta_range: dict    Change in expected range

    ctx: additional context (optional)
    """
    name = scenario.get("name", "Unnamed scenario")
    shocks = scenario.get("shocks", [])
    baseline = results.get("baseline", {})
    shocked = results.get("shocked", {})
    delta_direction = results.get("delta_direction", "unchanged")
    delta_range = results.get("delta_range", {})

    shocks_text = "\n".join(
        f"  - type={s.get('type', '?')}, {s}" for s in shocks
    ) if shocks else "  - None"

    user_content = (
        "Task: narrate_scenario\n\n"
        f"Scenario name: {name}\n"
        f"Shocks:\n{shocks_text}\n\n"
        f"Baseline forecast: direction={baseline.get('direction', 'N/A')}, "
        f"confidence={baseline.get('confidence', 'N/A')}, "
        f"expected_pct={baseline.get('expected_pct', 'N/A')}\n"
        f"Shocked forecast: direction={shocked.get('direction', 'N/A')}, "
        f"confidence={shocked.get('confidence', 'N/A')}, "
        f"expected_pct={shocked.get('expected_pct', 'N/A')}\n"
        f"Delta in directional pressure: {delta_direction}\n"
        f"Delta in expected range: {delta_range}\n\n"
        "Output a structured narrative with these sections, each 1-3 sentences:\n"
        "1. What the scenario assumes\n"
        "2. How the data would shift if the scenario plays out\n"
        "3. The directional pressure and confidence band, with the timeframe\n"
        "4. The strongest counterargument\n"
        "5. What data would validate or invalidate this scenario in the next 1-2 weeks\n\n"
        "Do not add any other sections."
    )

    return [
        {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_content}"},
    ]


def review_journal_entry_messages(entry: dict) -> list[dict]:  # type: ignore[type-arg]
    """
    Build messages for the review_journal_entry task.

    entry keys:
        hypothesis: str
        evidence: str | list
        confidence_pct: int | float
        planned_action: str
        risk_factors: str | list
        invalidation_criteria: str
    """
    hypothesis = entry.get("hypothesis", "N/A")
    evidence = entry.get("evidence", "N/A")
    confidence_pct = entry.get("confidence_pct", "N/A")
    planned_action = entry.get("planned_action", "N/A")
    risk_factors = entry.get("risk_factors", "N/A")
    invalidation_criteria = entry.get("invalidation_criteria", "N/A")

    # Normalise list fields
    if isinstance(evidence, list):
        evidence = "; ".join(str(e) for e in evidence)
    if isinstance(risk_factors, list):
        risk_factors = "; ".join(str(r) for r in risk_factors)

    user_content = (
        "Task: review_journal_entry\n\n"
        "Decision Journal Entry:\n"
        f"- Hypothesis: {hypothesis}\n"
        f"- Evidence: {evidence}\n"
        f"- Confidence: {confidence_pct}%\n"
        f"- Planned action: {planned_action}\n"
        f"- Risk factors: {risk_factors}\n"
        f"- Invalidation criteria: {invalidation_criteria}\n\n"
        "Review for decision quality, not endorsing the trade. Identify, in 4-6 short bullets:\n"
        "- one assumption that is implicit but not stated\n"
        "- one piece of evidence that would strengthen or weaken the hypothesis\n"
        "- one risk factor that is missing or underweighted\n"
        "- whether the invalidation criteria is testable and time-bound\n"
        "- whether the confidence_pct is consistent with the evidence weight\n"
        "- one process improvement for the next entry\n\n"
        "Do not say whether the trade is a good idea. Do not give a directional view."
    )

    return [
        {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_content}"},
    ]


def extract_event_messages(article: dict) -> list[dict]:  # type: ignore[type-arg]
    """
    Build messages for the extract_event task.

    article keys:
        title: str
        body: str
        source: str
        published_at: str
    """
    title = article.get("title", "N/A")
    body = article.get("body", "")
    source = article.get("source", "unknown")
    published_at = article.get("published_at", "unknown")

    # Truncate body to avoid excessive tokens
    body_snippet = body[:800] + ("..." if len(body) > 800 else "")

    user_content = (
        "Task: extract_event\n\n"
        "Article:\n"
        f"- Title: {title}\n"
        f"- Source: {source}\n"
        f"- Published: {published_at}\n"
        f"- Body (excerpt): {body_snippet}\n\n"
        "Extract the following fields and return ONLY a valid JSON object with no additional text:\n"
        '{\n'
        '  "category": "<supply|demand|weather|geopolitical|regulatory|other>",\n'
        '  "sentiment": <float -1.0 to 1.0>,\n'
        '  "impact_score": <float 0.0 to 1.0>,\n'
        '  "affected_regions": [<list of region strings>],\n'
        '  "entities": [<list of entity name strings>]\n'
        '}'
    )

    return [
        {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_content}"},
    ]
