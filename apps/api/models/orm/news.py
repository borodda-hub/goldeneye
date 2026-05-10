import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        Index("news_events_published_idx", "published_at"),
        Index("news_events_headline_trgm", "headline", postgresql_using="gin",
              postgresql_ops={"headline": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[float | None] = mapped_column(Numeric)
    impact_score: Mapped[float | None] = mapped_column(Numeric)
    affected_regions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    entities: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    ingested_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
