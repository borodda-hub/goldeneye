import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    shocks: Mapped[list] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    baseline_ref: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_forecasts.id"))
