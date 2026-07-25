"""Phase D2a — futures-curve vintage archive.

Adds `futures_curve_vintages`: one row per (vintage_date, symbol) holding
the curve snapshot the market adapter served ON that date. Yahoo drops
expired contract months (verified in PHASE_D2_PLAN §[V]), so the historical
front-of-curve is unreconstructible for free — this archive starts the
clock, exactly like 012's weather vintages.

Vintages are immutable history (insert-only repo, ON CONFLICT DO NOTHING);
`source` labels the configured adapter so mock vintages are excludable.

Revision ID: 013_curve_vintages
Revises: 012_weather_vintages
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_curve_vintages"
down_revision: Union[str, None] = "012_weather_vintages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "futures_curve_vintages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("vintage_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        # The adapter's get_curve_snapshot list, verbatim
        # ([{contract_code, expiry, mid_price}, ...]).
        sa.Column("curve", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "vintage_date", "symbol", name="uq_curve_vintage_date_symbol"
        ),
    )
    op.create_index(
        "ix_curve_vintages_vintage_date",
        "futures_curve_vintages",
        ["vintage_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_curve_vintages_vintage_date")
    op.drop_table("futures_curve_vintages")
