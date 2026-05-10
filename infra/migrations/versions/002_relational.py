"""Relational tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("exchange", sa.Text, nullable=False),
        sa.Column("asset_class", sa.Text, nullable=False, server_default="commodity"),
        sa.Column("currency", sa.Text, nullable=False, server_default="USD"),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("contract_size", sa.Numeric, nullable=False),
        sa.Column("tick_size", sa.Numeric, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("contract_code", sa.Text, nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("is_front_month", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("instrument_id", "contract_code", name="uq_contracts_instrument_code"),
    )
    op.create_index("contracts_front_month_idx", "contracts", ["instrument_id"],
                    postgresql_where=sa.text("is_front_month"))

    op.create_table(
        "eia_storage_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_date", sa.Date, nullable=False, unique=True),
        sa.Column("week_ending", sa.Date, nullable=False),
        sa.Column("total_lower_48_bcf", sa.Numeric, nullable=False),
        sa.Column("east_bcf", sa.Numeric),
        sa.Column("midwest_bcf", sa.Numeric),
        sa.Column("mountain_bcf", sa.Numeric),
        sa.Column("pacific_bcf", sa.Numeric),
        sa.Column("south_central_bcf", sa.Numeric),
        sa.Column("net_change_bcf", sa.Numeric, nullable=False),
        sa.Column("five_year_avg_bcf", sa.Numeric),
        sa.Column("five_year_max_bcf", sa.Numeric),
        sa.Column("five_year_min_bcf", sa.Numeric),
        sa.Column("consensus_estimate", sa.Numeric),
        sa.Column("surprise_bcf", sa.Numeric),
        sa.Column("source", sa.Text, nullable=False, server_default="EIA"),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "cot_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("release_date", sa.Date, nullable=False),
        sa.Column("contract_market_name", sa.Text, nullable=False),
        sa.Column("cftc_contract_market_code", sa.Text, nullable=False),
        sa.Column("producer_long", sa.BigInteger),
        sa.Column("producer_short", sa.BigInteger),
        sa.Column("swap_long", sa.BigInteger),
        sa.Column("swap_short", sa.BigInteger),
        sa.Column("managed_money_long", sa.BigInteger),
        sa.Column("managed_money_short", sa.BigInteger),
        sa.Column("other_reportable_long", sa.BigInteger),
        sa.Column("other_reportable_short", sa.BigInteger),
        sa.Column("nonreportable_long", sa.BigInteger),
        sa.Column("nonreportable_short", sa.BigInteger),
        sa.Column("open_interest_total", sa.BigInteger, nullable=False),
        sa.Column("managed_money_net", sa.BigInteger, sa.Computed("managed_money_long - managed_money_short", persisted=True)),
        sa.Column("source", sa.Text, nullable=False, server_default="CFTC_PRE"),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("report_date", "contract_market_name", name="uq_cot_reports_date_market"),
    )

    op.create_table(
        "news_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("url", sa.Text),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("category", sa.Text),
        sa.Column("sentiment", sa.Numeric),
        sa.Column("impact_score", sa.Numeric),
        sa.Column("affected_regions", postgresql.ARRAY(sa.Text)),
        sa.Column("entities", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("raw", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("news_events_published_idx", "news_events", [sa.text("published_at DESC")])
    op.execute("CREATE INDEX news_events_headline_trgm ON news_events USING gin (headline gin_trgm_ops)")

    op.create_table(
        "model_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("horizon", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("confidence", sa.Text, nullable=False),
        sa.Column("expected_pct", sa.Numeric),
        sa.Column("range_low_pct", sa.Numeric),
        sa.Column("range_high_pct", sa.Numeric),
        sa.Column("vol_regime", sa.Text),
        sa.Column("supporting", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("contradicting", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("features", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("inputs_hash", sa.Text),
        sa.Column("caveats", postgresql.ARRAY(sa.Text)),
    )
    op.create_index("model_forecasts_instrument_time_idx", "model_forecasts",
                    ["instrument_id", sa.text("generated_at DESC")])

    op.create_table(
        "scenario_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("shocks", postgresql.JSONB, nullable=False),
        sa.Column("result", postgresql.JSONB, nullable=False),
        sa.Column("baseline_ref", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_forecasts.id")),
    )

    op.create_table(
        "user_decision_journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence_pct", sa.Integer, nullable=False),
        sa.Column("planned_action", sa.Text),
        sa.Column("risk_factors", postgresql.ARRAY(sa.Text)),
        sa.Column("invalidation_criteria", sa.Text),
        sa.Column("outcome", sa.Text),
        sa.Column("reflection", sa.Text),
        sa.Column("llm_review", postgresql.JSONB),
        sa.CheckConstraint("confidence_pct BETWEEN 0 AND 100", name="ck_journal_confidence_pct"),
    )

    op.create_table(
        "paper_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id")),
        sa.Column("side", sa.Text, nullable=False),
        sa.Column("size_contracts", sa.Numeric, nullable=False),
        sa.Column("entry_price", sa.Numeric, nullable=False),
        sa.Column("exit_price", sa.Numeric),
        sa.Column("stop_loss", sa.Numeric),
        sa.Column("take_profit", sa.Numeric),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("rationale", sa.Text),
        sa.Column("outcome_pnl", sa.Numeric),
        sa.Column("reflection", sa.Text),
        sa.Column("journal_ref", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_decision_journals.id")),
    )
    op.create_index("paper_trades_user_status_idx", "paper_trades", ["user_id", "status"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False, server_default="info"),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default="false"),
    )

    op.create_table(
        "adapter_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("adapter_name", sa.Text, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("rows_ingested", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text),
    )
    op.create_index("adapter_runs_name_time_idx", "adapter_runs", ["adapter_name", sa.text("started_at DESC")])


def downgrade() -> None:
    op.drop_table("adapter_runs")
    op.drop_table("alerts")
    op.drop_table("paper_trades")
    op.drop_table("user_decision_journals")
    op.drop_table("scenario_runs")
    op.drop_table("model_forecasts")
    op.drop_table("news_events")
    op.drop_table("cot_reports")
    op.drop_table("eia_storage_reports")
    op.drop_table("contracts")
    op.drop_table("instruments")
