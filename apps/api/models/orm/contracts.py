import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("contracts_front_month_idx", "instrument_id", postgresql_where="is_front_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    contract_code: Mapped[str] = mapped_column(Text, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_front_month: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
