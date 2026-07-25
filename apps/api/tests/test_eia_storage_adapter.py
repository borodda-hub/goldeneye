"""Phase 31a.0 — natural-gas EIA adapter `_pivot` shape guards. Pure logic,
no network."""
from __future__ import annotations

from datetime import date, timedelta

from apps.api.adapters.energy.eia import SERIES_TOTAL, EIAAdapter


def _row(period: str, value: float) -> dict:
    return {"period": period, "series": SERIES_TOTAL, "value": str(value)}


def test_pivot_drops_boundary_row_with_no_net_change():
    """The oldest fetched week has no prior week to diff against. It must be
    dropped, not emitted with net_change_bcf=None — the table's NOT NULL
    constraint rejects that row the moment 31a persists these records."""
    out = EIAAdapter._pivot(
        [_row("2026-05-08", 1500.0), _row("2026-05-01", 1480.0), _row("2026-04-24", 1470.0)]
    )
    assert len(out) == 2  # boundary week 2026-04-24 dropped
    assert all(r["net_change_bcf"] is not None for r in out)
    assert out[0]["net_change_bcf"] == 20.0


def test_pivot_report_date_is_publication_thursday():
    out = EIAAdapter._pivot([_row("2026-05-08", 1500.0), _row("2026-05-01", 1480.0)])
    assert out[0]["week_ending"] == date(2026, 5, 8)
    assert out[0]["report_date"] == date(2026, 5, 8) + timedelta(days=6)


def test_pivot_no_consensus_fields_on_real_rows():
    """Real EIA publishes no analyst consensus — the fields stay None (the
    factor composite's seasonal-norm proxy carries the leg instead)."""
    out = EIAAdapter._pivot([_row("2026-05-08", 1500.0), _row("2026-05-01", 1480.0)])
    assert out[0]["consensus_estimate"] is None
    assert out[0]["surprise_bcf"] is None
