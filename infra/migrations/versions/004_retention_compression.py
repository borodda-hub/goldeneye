"""Retention and compression policies

Revision ID: 004
Revises: 003
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SELECT add_retention_policy('tick_data', INTERVAL '90 days')")
    op.execute("SELECT add_retention_policy('weather_forecasts', INTERVAL '180 days')")
    op.execute("ALTER TABLE price_bars SET (timescaledb.compress, timescaledb.compress_segmentby = 'contract_id,resolution')")
    op.execute("SELECT add_compression_policy('price_bars', INTERVAL '30 days')")


def downgrade() -> None:
    op.execute("SELECT remove_compression_policy('price_bars', if_exists => true)")
    op.execute("ALTER TABLE price_bars RESET (timescaledb.compress)")
    op.execute("SELECT remove_retention_policy('weather_forecasts', if_exists => true)")
    op.execute("SELECT remove_retention_policy('tick_data', if_exists => true)")
