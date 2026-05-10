"""Seed quality checks. Safe to run on empty DB — assertions only apply when data exists."""
import sys
from pathlib import Path


def run_checks(session) -> None:  # type: ignore[type-arg]
    from sqlalchemy import text

    def scalar(sql: str) -> int:
        return session.execute(text(sql)).scalar() or 0

    bar_count = scalar("SELECT COUNT(*) FROM price_bars")
    if bar_count > 0:
        bad_ohlc = scalar(
            "SELECT COUNT(*) FROM price_bars WHERE high < low OR open < low OR open > high OR close < low OR close > high"
        )
        assert bad_ohlc == 0, f"{bad_ohlc} price_bars rows fail OHLC invariants"

    cot_count = scalar("SELECT COUNT(*) FROM cot_reports")
    if cot_count > 0:
        pass  # COT category-sum checks implemented in Phase 02

    eia_count = scalar("SELECT COUNT(*) FROM eia_storage_reports")
    if eia_count > 0:
        pass  # Region-split sum checks implemented in Phase 02


if __name__ == "__main__":
    import asyncio
    from apps.api.db.session import get_session_factory

    async def main() -> None:
        async with get_session_factory()() as session:
            try:
                run_checks(session)
                print("validate: all checks passed")
            except AssertionError as e:
                print(f"validate: FAILED — {e}", file=sys.stderr)
                sys.exit(1)

    asyncio.run(main())
