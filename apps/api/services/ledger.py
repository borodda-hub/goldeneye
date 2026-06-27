"""Phase B4 — decision/audit ledger service.

Pure helpers: the canonical hash (chain integrity), the per-event payload
builders, and the best-effort "what the system knew at decision time" capture.

The hash chain is what makes the ledger tamper-EVIDENT: each event's `row_hash`
is derived from the previous event's hash + this event's content, so any
out-of-band edit (one that bypasses the DB immutability trigger) breaks the
chain and is detectable by `repos.ledger.verify_chain`.

System-context capture is best-effort and **never silently omits**: if it can't
be computed it records an explicit absence (`{captured: false, reason: ...}`) so
the audit trail shows *that* it didn't know, and why — not a hole.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal


def canonical_hash(
    *,
    prev_hash: str | None,
    decision_id: uuid.UUID,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, Any],
) -> str:
    """Deterministic SHA-256 over (prev_hash, decision_id, event_type,
    occurred_at, payload). Stable key ordering + ISO timestamp so the digest is
    reproducible by the verifier."""
    material = {
        "prev_hash": prev_hash,
        "decision_id": str(decision_id),
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "payload": payload,
    }
    serialized = json.dumps(
        material, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _f(value: Any) -> float | None:
    return float(value) if value is not None else None


def build_created_payload(
    entry: UserDecisionJournal, *, system_context: dict[str, Any]
) -> dict[str, Any]:
    """The 'at the moment of decision, here is exactly what you knew' snapshot —
    the user's inputs (write-once journal fields) plus the system context.

    `system_context` is always present: either the captured snapshot or an
    explicit recorded absence (see `capture_system_context`)."""
    return {
        "user_inputs": {
            "hypothesis": entry.hypothesis,
            "evidence": entry.evidence,
            "confidence_pct": entry.confidence_pct,
            "planned_action": entry.planned_action,
            "risk_factors": entry.risk_factors,
            "invalidation_criteria": entry.invalidation_criteria,
            "predicted_direction": entry.predicted_direction,
            "horizon_days": entry.horizon_days,
            "threshold_pct": _f(entry.threshold_pct),
            "anchor_price": _f(entry.anchor_price),
            "thesis_id_at_write": (
                str(entry.thesis_id_at_write) if entry.thesis_id_at_write else None
            ),
            "thesis_conviction_at_write": entry.thesis_conviction_at_write,
        },
        "system_context": system_context,
    }


def build_resolved_payload(
    *,
    outcome: str,
    resolved_at: datetime | None,
    auto_resolved: bool,
    anchor_price: float | None,
    realized_close: float | None,
    move_pct: float | None,
    deadband_pct: float | None,
) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "resolved_at": resolved_at.isoformat() if resolved_at else None,
        "auto_resolved": auto_resolved,
        "anchor_price": anchor_price,
        "realized_close": realized_close,
        "move_pct": move_pct,
        "deadband_pct": deadband_pct,
    }


def build_amended_payload(
    *, field: str, old: Any, new: Any
) -> dict[str, Any]:
    return {"field": field, "old": old, "new": new}


async def capture_system_context(
    session: AsyncSession, *, instrument: Any, instrument_code: str
) -> dict[str, Any]:
    """Best-effort snapshot of what the SYSTEM knew at decision time — the
    ensemble directional read, the vol band/regime, the model lineup.

    Reuses the exact computation the signals/forecast endpoints already call (no
    new model, no new calibration feature). On ANY failure it returns an explicit
    recorded absence — it never raises (a decision write must not be blocked) and
    never silently omits context.
    """
    try:
        # Imported lazily so a journal write never hard-depends on the forecast
        # stack at import time (and to keep the capture self-contained).
        from apps.api.repos import contracts as contract_repo
        from apps.api.services.ensemble import compute_ensemble
        from apps.api.services.model_calibration import model_weights_for
        from apps.api.services.model_registry import ForecastContext, run_all
        from apps.api.services.models.vol_range import predict
        from apps.api.services.price_lookup import get_latest_closes

        front = await contract_repo.get_front_month(session, instrument.id)
        closes = await get_latest_closes(
            session,
            contract_id=front.id if front else None,
            contract_code=front.contract_code if front else None,
            n=250,
        )
        if len(closes) < 30:
            return {
                "captured": False,
                "reason": "unavailable: insufficient price history (<30 closes)",
            }

        ctx = ForecastContext(
            symbol=instrument_code,
            closes=closes,
            latest_storage=None,
            latest_cot=None,
        )
        results = await run_all(ctx)
        weights = await model_weights_for(session, instrument.id, "1d")
        ensemble = compute_ensemble(results, model_weights=weights)
        rng = predict(closes, "1w", "har_log")

        return {
            "captured": True,
            "as_of": datetime.now(UTC).isoformat(),
            "ensemble": {
                "direction": ensemble.get("direction"),
                "confidence": ensemble.get("confidence"),
                "agreement": ensemble.get("agreement"),
                "vol_regime": ensemble.get("vol_regime"),
                "expected_pct": ensemble.get("expected_pct"),
                "range": ensemble.get("range"),
            },
            "range_1w": asdict(rng) if rng is not None else None,
            "model_lineup": [r.model_name for r in results],
        }
    except Exception as exc:  # noqa: BLE001 — capture must never block a write
        return {
            "captured": False,
            "reason": f"unavailable: {type(exc).__name__}",
        }
