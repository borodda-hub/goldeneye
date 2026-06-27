"""Phase B4 — immutable decision/audit ledger ORM.

An append-only event log shadowing `user_decision_journals`. See
`infra/migrations/versions/011_decision_ledger.py` for the immutability trigger
(DB-enforced no UPDATE/DELETE) and the `source='live'` CHECK. The repo
(`repos/ledger.py`) exposes only append + read — there is no update/delete path.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class DecisionLedgerEvent(Base):
    __tablename__ = "decision_ledger_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # DB-assigned global append order (Identity always → not set by the app).
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True))
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="live"
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prev_hash: Mapped[str | None] = mapped_column(Text)
    row_hash: Mapped[str] = mapped_column(Text, nullable=False)
