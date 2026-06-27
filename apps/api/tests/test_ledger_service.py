"""Phase B4 — pure ledger logic (hash chain + payloads). No DB.

The DB-enforced immutability + tamper-evidence are locked end-to-end in
`tests/db/test_ledger_e2e.py` (gated). These fast units pin the hashing logic the
chain depends on, so a refactor can't silently weaken tamper-detection.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.api.models.orm.ledger import DecisionLedgerEvent
from apps.api.repos.ledger import verify_chain
from apps.api.services.ledger import (
    build_amended_payload,
    build_created_payload,
    canonical_hash,
)

_DT = datetime(2026, 1, 1, tzinfo=UTC)


def _hash(did, prev, etype, payload):
    return canonical_hash(
        prev_hash=prev, decision_id=did, event_type=etype,
        occurred_at=_DT, payload=payload,
    )


def test_canonical_hash_is_deterministic_and_content_sensitive():
    did = uuid.uuid4()
    h1 = _hash(did, None, "created", {"a": 1, "b": 2})
    h2 = _hash(did, None, "created", {"b": 2, "a": 1})  # key order irrelevant
    assert h1 == h2
    assert _hash(did, None, "created", {"a": 1}) != h1  # payload change → new hash
    assert _hash(did, "prev", "created", {"a": 1, "b": 2}) != h1  # prev change → new hash


def _event(did, seq, prev, etype, payload):
    ev = DecisionLedgerEvent(
        id=uuid.uuid4(), decision_id=did, user_id=None, event_type=etype,
        occurred_at=_DT, payload=payload, prev_hash=prev,
        row_hash=_hash(did, prev, etype, payload),
    )
    ev.seq = seq
    return ev


def test_verify_chain_accepts_intact_and_detects_tamper():
    did = uuid.uuid4()
    e1 = _event(did, 1, None, "created", {"hypothesis": "x"})
    e2 = _event(did, 2, e1.row_hash, "resolved", {"outcome": "hit"})
    assert verify_chain([e1, e2])["ok"] is True
    assert verify_chain([])["ok"] is True  # empty chain is ok

    # Tamper a payload in place — the stored row_hash no longer matches.
    e2.payload = {"outcome": "miss"}
    result = verify_chain([e1, e2])
    assert result["ok"] is False
    assert result["broken_at_seq"] == 2


def test_created_payload_always_carries_system_context():
    class _Entry:
        hypothesis = "h"
        evidence: list = []
        confidence_pct = 60
        planned_action = None
        risk_factors = None
        invalidation_criteria = None
        predicted_direction = "bullish"
        horizon_days = 10
        threshold_pct = 1.0
        anchor_price = 100.0
        thesis_id_at_write = None
        thesis_conviction_at_write = None

    absent = {"captured": False, "reason": "unavailable: insufficient price history"}
    payload = build_created_payload(_Entry(), system_context=absent)
    assert payload["system_context"] == absent  # recorded absence, never omitted
    assert payload["user_inputs"]["predicted_direction"] == "bullish"


def test_amended_payload_records_old_and_new():
    p = build_amended_payload(field="reflection", old=None, new="learned X")
    assert p == {"field": "reflection", "old": None, "new": "learned X"}
