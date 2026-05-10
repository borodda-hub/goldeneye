import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Enum("info", "warning", "critical", name="alert_severity_t"), nullable=False, server_default="info")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
