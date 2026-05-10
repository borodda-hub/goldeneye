import uuid
from datetime import datetime

from sqlalchemy import ARRAY, CheckConstraint, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class UserDecisionJournal(Base):
    __tablename__ = "user_decision_journals"
    __table_args__ = (
        CheckConstraint("confidence_pct BETWEEN 0 AND 100", name="ck_journal_confidence_pct"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    confidence_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_action: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    invalidation_criteria: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    reflection: Mapped[str | None] = mapped_column(Text)
    llm_review: Mapped[dict | None] = mapped_column(JSONB)
