"""Hypertable tables and create_hypertable calls

Revision ID: 003
Revises: 002
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_bars",
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False, primary_key=True),
        sa.Column("resolution", sa.Text, nullable=False, primary_key=True),
        sa.Column("open", sa.Numeric, nullable=False),
        sa.Column("high", sa.Numeric, nullable=False),
        sa.Column("low", sa.Numeric, nullable=False),
        sa.Column("close", sa.Numeric, nullable=False),
        sa.Column("volume", sa.BigInteger),
        sa.Column("source", sa.Text, nullable=False, server_default="mock"),
    )
    op.execute("SELECT create_hypertable('price_bars', 'ts', chunk_time_interval => INTERVAL '7 days')")

    op.create_table(
        "tick_data",
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False, primary_key=True),
        sa.Column("price", sa.Numeric, nullable=False),
        sa.Column("size", sa.BigInteger, nullable=False),
        sa.Column("side", sa.Text),
        sa.Column("source", sa.Text, nullable=False, server_default="mock"),
    )
    op.execute("SELECT create_hypertable('tick_data', 'ts', chunk_time_interval => INTERVAL '1 day')")

    op.create_table(
        "futures_curve_snapshots",
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False, primary_key=True),
        sa.Column("curve", postgresql.JSONB, nullable=False),
    )
    op.execute("SELECT create_hypertable('futures_curve_snapshots', 'ts', chunk_time_interval => INTERVAL '30 days')")

    op.create_table(
        "weather_observations",
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("region", sa.Text, nullable=False, primary_key=True),
        sa.Column("temp_f", sa.Numeric),
        sa.Column("hdd", sa.Numeric),
        sa.Column("cdd", sa.Numeric),
        sa.Column("precip_in", sa.Numeric),
        sa.Column("anomaly_f", sa.Numeric),
        sa.Column("source", sa.Text, nullable=False, server_default="mock"),
    )
    op.execute("SELECT create_hypertable('weather_observations', 'ts', chunk_time_interval => INTERVAL '30 days')")

    op.create_table(
        "weather_forecasts",
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("issued_at", sa.TIMESTAMP(timezone=True), nullable=False, primary_key=True),
        sa.Column("region", sa.Text, nullable=False, primary_key=True),
        sa.Column("horizon_days", sa.Integer, nullable=False),
        sa.Column("temp_f", sa.Numeric),
        sa.Column("hdd", sa.Numeric),
        sa.Column("cdd", sa.Numeric),
        sa.Column("anomaly_f", sa.Numeric),
        sa.Column("source", sa.Text, nullable=False, server_default="mock"),
    )
    op.execute("SELECT create_hypertable('weather_forecasts', 'issued_at', chunk_time_interval => INTERVAL '7 days')")


def downgrade() -> None:
    op.drop_table("weather_forecasts")
    op.drop_table("weather_observations")
    op.drop_table("futures_curve_snapshots")
    op.drop_table("tick_data")
    op.drop_table("price_bars")
