"""ORM model for the `theses` table (Phase 12 — Working Thesis card)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class Thesis(Base):
    __tablename__ = "theses"
    __table_args__ = (
        CheckConstraint(
            "conviction_pct BETWEEN 0 AND 100", name="ck_theses_conviction_pct"
        ),
        CheckConstraint(
            "char_length(statement) > 0", name="ck_theses_statement_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Owner (Clerk user). NULL = the shared anonymous/demo pool. Populated +
    # enforced in B3b; the column + scoping capability land here in B3a.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    instrument_code: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="NG"
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    contradicting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    missing_data: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    conviction_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
