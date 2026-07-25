"""Phase D5 — weather-forecast vintage archive.

Adds `weather_forecast_vintages`: one row per (vintage_date, region) holding
the forecast the platform's weather adapter served ON that date. Forecasts
are unbacktestable without an archive of what was believed at the time —
this table starts that clock (MASTER_PLAN §4 D5).

Vintages are immutable history by convention + repo design (insert-only,
ON CONFLICT DO NOTHING): a past vintage is never updated. The `source`
column records the configured adapter (`nws` / `mock`) so mock vintages are
labeled and excludable from any future validation.

Revision ID: 012_weather_vintages
Revises: 011_decision_ledger
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_weather_vintages"
down_revision: Union[str, None] = "011_decision_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weather_forecast_vintages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("vintage_date", sa.Date(), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        # The adapter's per-day forecast list, verbatim (schema-flexible on
        # purpose — we archive what was served, shape drift included).
        sa.Column("forecast", postgresql.JSONB(), nullable=False),
        # Populated on the region='US' aggregate row only.
        sa.Column("national_hdd_anomaly", sa.Numeric(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "vintage_date", "region", name="uq_weather_vintage_date_region"
        ),
    )
    op.create_index(
        "ix_weather_vintages_vintage_date",
        "weather_forecast_vintages",
        ["vintage_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_weather_vintages_vintage_date")
    op.drop_table("weather_forecast_vintages")
