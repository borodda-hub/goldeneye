import uuid
from datetime import datetime

from sqlalchemy import Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    exchange: Mapped[str] = mapped_column(Text, nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False, server_default="commodity")
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="USD")
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    contract_size: Mapped[float] = mapped_column(Numeric, nullable=False)
    tick_size: Mapped[float] = mapped_column(Numeric, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
