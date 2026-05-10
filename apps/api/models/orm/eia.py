import uuid
from datetime import date, datetime

from sqlalchemy import Date, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class EIAStorageReport(Base):
    __tablename__ = "eia_storage_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    week_ending: Mapped[date] = mapped_column(Date, nullable=False)
    total_lower_48_bcf: Mapped[float] = mapped_column(Numeric, nullable=False)
    east_bcf: Mapped[float | None] = mapped_column(Numeric)
    midwest_bcf: Mapped[float | None] = mapped_column(Numeric)
    mountain_bcf: Mapped[float | None] = mapped_column(Numeric)
    pacific_bcf: Mapped[float | None] = mapped_column(Numeric)
    south_central_bcf: Mapped[float | None] = mapped_column(Numeric)
    net_change_bcf: Mapped[float] = mapped_column(Numeric, nullable=False)
    five_year_avg_bcf: Mapped[float | None] = mapped_column(Numeric)
    five_year_max_bcf: Mapped[float | None] = mapped_column(Numeric)
    five_year_min_bcf: Mapped[float | None] = mapped_column(Numeric)
    consensus_estimate: Mapped[float | None] = mapped_column(Numeric)
    surprise_bcf: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="EIA")
    fetched_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
