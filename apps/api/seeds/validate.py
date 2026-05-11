"""Seed quality checks. Safe to run on empty DB — assertions only apply when data exists."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def run_checks(session) -> None:  # type: ignore[type-arg]
    """
    Run seed data quality checks against the database.

    Safe to call on an empty DB — each check is gated on row count.
    Can be called from async context by passing the async session;
    the SQL executed here is synchronous-style (execute returns a result directly
    when called within an already-running transaction).

    Args:
        session: SQLAlchemy AsyncSession (called from async context via await, or
                 sync session for direct use).
    """
    from sqlalchemy import text

    def scalar(sql: str) -> int:
        result = session.execute(text(sql))
        # Support both sync and async-style results
        if hasattr(result, "__await__"):
            raise RuntimeError("run_checks must be called with a sync-compatible session execute; "
                               "use run_checks_async for async sessions")
        val = result.scalar()
        return int(val) if val is not None else 0

    # ── OHLC invariants ─────────────────────────────────────────────────────
    bar_count = scalar("SELECT COUNT(*) FROM price_bars")
    if bar_count > 0:
        bad_ohlc = scalar(
            "SELECT COUNT(*) FROM price_bars "
            "WHERE high < low "
            "   OR open < low OR open > high "
            "   OR close < low OR close > high"
        )
        assert bad_ohlc == 0, f"{bad_ohlc} price_bars rows fail OHLC invariants"

    # ── COT non-negative position columns ──────────────────────────────────
    cot_count = scalar("SELECT COUNT(*) FROM cot_reports")
    if cot_count > 0:
        position_cols = [
            "producer_long", "producer_short",
            "swap_long", "swap_short",
            "managed_money_long", "managed_money_short",
            "other_reportable_long", "other_reportable_short",
            "nonreportable_long", "nonreportable_short",
        ]
        for col in position_cols:
            bad_neg = scalar(
                f"SELECT COUNT(*) FROM cot_reports WHERE {col} < 0"
            )
            assert bad_neg == 0, f"{bad_neg} cot_reports rows have negative {col}"

    # ── EIA region splits sum to total ──────────────────────────────────────
    eia_count = scalar("SELECT COUNT(*) FROM eia_storage_reports")
    if eia_count > 0:
        # Check that region sum ≈ total (within 1 Bcf rounding)
        bad_sum = scalar(
            """
            SELECT COUNT(*) FROM eia_storage_reports
            WHERE ABS(
                COALESCE(east_bcf, 0) + COALESCE(midwest_bcf, 0) +
                COALESCE(mountain_bcf, 0) + COALESCE(pacific_bcf, 0) +
                COALESCE(south_central_bcf, 0) - total_lower_48_bcf
            ) > 1.0
            """
        )
        assert bad_sum == 0, (
            f"{bad_sum} eia_storage_reports rows where region sum differs from total by >1 Bcf"
        )

    # ── Weather forecast horizons: 1–14 for each region ─────────────────────
    weather_fcast_count = scalar("SELECT COUNT(*) FROM weather_forecasts")
    if weather_fcast_count > 0:
        regions = [
            "northeast", "midwest", "mountain",
            "pacific", "south_central", "southeast",
        ]
        issued_at_check = "2026-05-10 12:00:00"
        for region in regions:
            horizon_count = scalar(
                f"""
                SELECT COUNT(DISTINCT horizon_days)
                FROM weather_forecasts
                WHERE region = '{region}'
                  AND issued_at = '{issued_at_check}'
                  AND horizon_days BETWEEN 1 AND 14
                """
            )
            assert horizon_count == 14, (
                f"Region '{region}' has {horizon_count}/14 forecast horizons "
                f"for issued_at={issued_at_check!r}"
            )


async def run_checks_async(session) -> None:  # type: ignore[type-arg]
    """
    Async version of run_checks for use directly from async contexts
    where session.execute returns a coroutine.
    """
    from sqlalchemy import text

    async def scalar(sql: str) -> int:
        result = await session.execute(text(sql))
        val = result.scalar()
        return int(val) if val is not None else 0

    # ── OHLC invariants ─────────────────────────────────────────────────────
    bar_count = await scalar("SELECT COUNT(*) FROM price_bars")
    if bar_count > 0:
        bad_ohlc = await scalar(
            "SELECT COUNT(*) FROM price_bars "
            "WHERE high < low "
            "   OR open < low OR open > high "
            "   OR close < low OR close > high"
        )
        assert bad_ohlc == 0, f"{bad_ohlc} price_bars rows fail OHLC invariants"

    # ── COT non-negative position columns ──────────────────────────────────
    cot_count = await scalar("SELECT COUNT(*) FROM cot_reports")
    if cot_count > 0:
        position_cols = [
            "producer_long", "producer_short",
            "swap_long", "swap_short",
            "managed_money_long", "managed_money_short",
            "other_reportable_long", "other_reportable_short",
            "nonreportable_long", "nonreportable_short",
        ]
        for col in position_cols:
            bad_neg = await scalar(
                f"SELECT COUNT(*) FROM cot_reports WHERE {col} < 0"
            )
            assert bad_neg == 0, f"{bad_neg} cot_reports rows have negative {col}"

    # ── EIA region splits sum to total ──────────────────────────────────────
    eia_count = await scalar("SELECT COUNT(*) FROM eia_storage_reports")
    if eia_count > 0:
        bad_sum = await scalar(
            """
            SELECT COUNT(*) FROM eia_storage_reports
            WHERE ABS(
                COALESCE(east_bcf, 0) + COALESCE(midwest_bcf, 0) +
                COALESCE(mountain_bcf, 0) + COALESCE(pacific_bcf, 0) +
                COALESCE(south_central_bcf, 0) - total_lower_48_bcf
            ) > 1.0
            """
        )
        assert bad_sum == 0, (
            f"{bad_sum} eia_storage_reports rows where region sum differs from total by >1 Bcf"
        )

    # ── Weather forecast horizons: 1–14 for each region ─────────────────────
    weather_fcast_count = await scalar("SELECT COUNT(*) FROM weather_forecasts")
    if weather_fcast_count > 0:
        regions = [
            "northeast", "midwest", "mountain",
            "pacific", "south_central", "southeast",
        ]
        issued_at_check = "2026-05-10 12:00:00"
        for region in regions:
            horizon_count = await scalar(
                f"""
                SELECT COUNT(DISTINCT horizon_days)
                FROM weather_forecasts
                WHERE region = '{region}'
                  AND issued_at = '{issued_at_check}'
                  AND horizon_days BETWEEN 1 AND 14
                """
            )
            assert horizon_count == 14, (
                f"Region '{region}' has {horizon_count}/14 forecast horizons "
                f"for issued_at={issued_at_check!r}"
            )


if __name__ == "__main__":
    import asyncio
    from apps.api.db.session import get_session_factory

    async def _main() -> None:
        async with get_session_factory()() as session:
            try:
                await run_checks_async(session)
                print("validate: all checks passed")
            except AssertionError as e:
                print(f"validate: FAILED — {e}", file=sys.stderr)
                sys.exit(1)

    asyncio.run(_main())
