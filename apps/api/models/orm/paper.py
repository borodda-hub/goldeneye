import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        Index("paper_trades_user_status_idx", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opened_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contracts.id"))
    side: Mapped[str] = mapped_column(Text, nullable=False)
    size_contracts: Mapped[float] = mapped_column(Numeric, nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Numeric)
    stop_loss: Mapped[float | None] = mapped_column(Numeric)
    take_profit: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    rationale: Mapped[str | None] = mapped_column(Text)
    outcome_pnl: Mapped[float | None] = mapped_column(Numeric)
    reflection: Mapped[str | None] = mapped_column(Text)
    journal_ref: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_decision_journals.id"))
