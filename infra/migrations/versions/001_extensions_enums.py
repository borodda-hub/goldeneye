"""Extensions and enums

Revision ID: 001
Revises:
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("CREATE TYPE direction_t AS ENUM ('bullish','bearish','neutral')")
    op.execute("CREATE TYPE confidence_t AS ENUM ('low','medium','high')")
    op.execute("CREATE TYPE volatility_regime_t AS ENUM ('compressed','normal','elevated','crisis')")
    op.execute("CREATE TYPE bar_resolution_t AS ENUM ('1m','5m','15m','1h','1d')")
    op.execute("CREATE TYPE trade_side_t AS ENUM ('long','short')")
    op.execute("CREATE TYPE trade_status_t AS ENUM ('open','closed','cancelled')")
    op.execute("CREATE TYPE alert_severity_t AS ENUM ('info','warning','critical')")
    op.execute("CREATE TYPE adapter_health_t AS ENUM ('ok','degraded','down','unknown')")


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS adapter_health_t")
    op.execute("DROP TYPE IF EXISTS alert_severity_t")
    op.execute("DROP TYPE IF EXISTS trade_status_t")
    op.execute("DROP TYPE IF EXISTS trade_side_t")
    op.execute("DROP TYPE IF EXISTS bar_resolution_t")
    op.execute("DROP TYPE IF EXISTS volatility_regime_t")
    op.execute("DROP TYPE IF EXISTS confidence_t")
    op.execute("DROP TYPE IF EXISTS direction_t")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
