"""Decision-quality coaching service (Phase 13.8).

Wraps the existing calibration + journal data and asks the LLM to synthesize
per-bucket coaching: what patterns appear in winning vs losing entries,
plus a one-line recommendation per bucket and an overall synthesis.

Returns structured JSON with a safety envelope. Not cached at the service
level — the calibration page calls this on mount, and a short HTTP-level
cache on the frontend (~10 min staleTime) is enough.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.repos import journal as journal_repo
from apps.api.services.calibration import (
    CalibrationResult,
    compute_calibration,
)
from apps.api.services.llm_explainer import _call_with_safety_check
from apps.api.services.llm_prompts import coach_dq_messages
from apps.api.services.llm_routing import select_model
from apps.api.services.safety import SafetyEnvelope, wrap_with_uncertainty

logger = logging.getLogger(__name__)


def _calibration_to_dict(cal: CalibrationResult) -> dict[str, Any]:
    return {
        "instrument_code": cal.instrument_code,
        "buckets": [
            {
                "label": b.label,
                "lower_pct": b.lower_pct,
                "upper_pct": b.upper_pct,
                "claimed_mean": b.claimed_mean,
                "total_count": b.total_count,
                "resolved_count": b.resolved_count,
                "hit_count": b.hit_count,
                "hit_rate": b.hit_rate,
            }
            for b in cal.buckets
        ],
        "total_entries": cal.total_entries,
        "resolved_entries": cal.resolved_entries,
        "unresolved_entries": cal.unresolved_entries,
        "summary": cal.summary,
    }


def _entry_to_prompt_dict(entry: Any) -> dict[str, Any]:
    """Shape a journal ORM row into the dict the prompt builder expects."""
    return {
        "hypothesis": entry.hypothesis,
        "thesis_conviction_at_write": entry.thesis_conviction_at_write,
        "confidence_pct": entry.confidence_pct,
        "resolved_direction": entry.resolved_direction,
    }


def _parse_coaching_json(text: str) -> dict[str, Any]:
    """Parse the LLM's JSON output; degrade to an empty result on failure."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner_lines = lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]
        stripped = "\n".join(inner_lines)
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse coach_dq JSON: %s. Text: %r", exc, text[:200]
        )
        return {
            "buckets": [],
            "overall": {"synthesis": "", "top_recommendation": ""},
        }

    raw_buckets = data.get("buckets") or []
    buckets: list[dict[str, Any]] = []
    for b in raw_buckets:
        if not isinstance(b, dict):
            continue
        buckets.append(
            {
                "label": str(b.get("label", "")),
                "effective_patterns": [
                    str(s) for s in (b.get("effective_patterns") or [])
                ][:3],
                "failure_patterns": [
                    str(s) for s in (b.get("failure_patterns") or [])
                ][:3],
                "recommendation": str(b.get("recommendation", "")),
            }
        )

    overall_raw = data.get("overall") or {}
    overall = {
        "synthesis": str(overall_raw.get("synthesis", "")),
        "top_recommendation": str(overall_raw.get("top_recommendation", "")),
    }
    return {"buckets": buckets, "overall": overall}


async def coach_decision_quality(
    session: AsyncSession,
    *,
    instrument_id: Any,
    instrument_code: str,
    bucket_count: int = 5,
) -> tuple[dict[str, Any], SafetyEnvelope]:
    """Run LLM coaching against the analyst's journal + calibration.

    Returns ({buckets, overall}, safety_envelope). When there are zero
    resolved entries, returns empty coaching with a safety envelope flagging
    the small-sample caveat so the UI can render a useful empty state
    without hitting the LLM.
    """
    calibration = await compute_calibration(
        session,
        instrument_id=instrument_id,
        instrument_code=instrument_code,
        bucket_count=bucket_count,
    )
    entries_orm = await journal_repo.list_with_resolutions(
        session, instrument_id
    )
    entries_dicts = [_entry_to_prompt_dict(e) for e in entries_orm]

    resolved_count = sum(
        1
        for e in entries_dicts
        if e["resolved_direction"] in ("hit", "miss")
    )

    if resolved_count == 0:
        envelope = wrap_with_uncertainty(
            {},
            confidence="low",
            caveats=[
                "No resolved journal entries yet. Coaching is unavailable until "
                "at least 3 entries have a hit or miss resolution.",
                "Coaching assesses decision quality only, not the merits of any "
                "specific position.",
            ],
            as_of=datetime.utcnow(),
        )
        return (
            {
                "buckets": [],
                "overall": {
                    "synthesis": "",
                    "top_recommendation": "",
                },
            },
            envelope,
        )

    prompt = coach_dq_messages(_calibration_to_dict(calibration), entries_dicts)
    model = select_model("coach_dq", {"resolved_count": resolved_count})
    text = await _call_with_safety_check("coach_dq", prompt, model=model)
    parsed = _parse_coaching_json(text)

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium" if resolved_count >= 10 else "low",
        caveats=[
            "Coaching assesses decision quality patterns, not the merits of any "
            "specific position.",
            "Small samples lead to noisy patterns. Bucket commentary improves "
            "as more entries are resolved.",
            "Model outputs are statistical inferences only, not financial advice.",
        ],
        as_of=datetime.utcnow(),
    )
    return (parsed, envelope)
