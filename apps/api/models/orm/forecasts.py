import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class ModelForecast(Base):
    __tablename__ = "model_forecasts"
    __table_args__ = (
        Index("model_forecasts_instrument_time_idx", "instrument_id", "generated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    horizon: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    expected_pct: Mapped[float | None] = mapped_column(Numeric)
    range_low_pct: Mapped[float | None] = mapped_column(Numeric)
    range_high_pct: Mapped[float | None] = mapped_column(Numeric)
    vol_regime: Mapped[str | None] = mapped_column(Text)
    supporting: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    contradicting: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    inputs_hash: Mapped[str | None] = mapped_column(Text)
    caveats: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
