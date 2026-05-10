import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Computed, Date, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class COTReport(Base):
    __tablename__ = "cot_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_market_name: Mapped[str] = mapped_column(Text, nullable=False)
    cftc_contract_market_code: Mapped[str] = mapped_column(Text, nullable=False)
    producer_long: Mapped[int | None] = mapped_column(BigInteger)
    producer_short: Mapped[int | None] = mapped_column(BigInteger)
    swap_long: Mapped[int | None] = mapped_column(BigInteger)
    swap_short: Mapped[int | None] = mapped_column(BigInteger)
    managed_money_long: Mapped[int | None] = mapped_column(BigInteger)
    managed_money_short: Mapped[int | None] = mapped_column(BigInteger)
    other_reportable_long: Mapped[int | None] = mapped_column(BigInteger)
    other_reportable_short: Mapped[int | None] = mapped_column(BigInteger)
    nonreportable_long: Mapped[int | None] = mapped_column(BigInteger)
    nonreportable_short: Mapped[int | None] = mapped_column(BigInteger)
    open_interest_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    managed_money_net: Mapped[int | None] = mapped_column(
        BigInteger,
        Computed("managed_money_long - managed_money_short", persisted=True),
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="CFTC_PRE")
    fetched_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
