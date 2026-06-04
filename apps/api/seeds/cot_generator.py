"""
Generates weekly CFTC Commitments of Traders (disaggregated) reports.
100 weekly reports per symbol.

Algorithm (from docs/MOCK_DATA_SPEC.md):
- Open interest baseline drifts ±10% over 2 years (per-symbol baseline below).
- Managed money net oscillates within a per-symbol band, momentum-following
  (AR(1) oscillator), with long/short derived from net + a long bias.
- Producer net is the inverse of managed-money net with smoothing.
- Swap dealer relatively stable; other reportable small; nonreportable is the
  residual that makes categories sum to open interest.

Phase 17 generalized this from NG-only to a per-symbol table. Every absolute
magnitude (baselines, biases, noise std, OI floor) scales by
`oi_baseline / NG_OI_BASELINE`, and each symbol draws from its own seeded RNG,
so the demo is reproducible and each market is plausibly sized. NG keeps
`seed=42` and `oi_baseline=1,400,000`, so its output is byte-identical to the
pre-Phase-17 generator.

report_date is Tuesday, release_date is the following Friday.

Return list[dict] with all cot_reports columns except id, fetched_at,
managed_money_net (the DB computes the generated column).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

NG_OI_BASELINE = 1_400_000
# NG managed-money band; used to scale the AR(1) innovation per symbol.
_NG_MM_BAND = 400_000  # 250_000 - (-150_000)


class SymbolCotParams(NamedTuple):
    """Per-symbol COT generation parameters."""

    contract_market_name: str
    cftc_contract_market_code: str
    oi_baseline: int
    mm_net_min: int
    mm_net_max: int
    seed: int


# Open-interest baselines and managed-money bands differ by an order of
# magnitude across these markets. CFTC codes match cftc.py::MARKETS and
# instruments.json metadata.
COT_PARAMS: dict[str, SymbolCotParams] = {
    "NG": SymbolCotParams(
        "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE", "023651",
        1_400_000, -150_000, 250_000, 42,
    ),
    "CL": SymbolCotParams(
        "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE", "067651",
        1_800_000, -100_000, 400_000, 43,
    ),
    "HO": SymbolCotParams(
        "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE", "022651",
        300_000, -40_000, 80_000, 44,
    ),
    "RB": SymbolCotParams(
        "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE", "111659",
        300_000, -30_000, 90_000, 45,
    ),
    "GC": SymbolCotParams(
        "GOLD - COMMODITY EXCHANGE INC.", "088691",
        500_000, -50_000, 250_000, 46,
    ),
    "SI": SymbolCotParams(
        "SILVER - COMMODITY EXCHANGE INC.", "084691",
        150_000, -20_000, 60_000, 47,
    ),
}

# Backwards-compat exports (NG values).
CONTRACT_MARKET_NAME = COT_PARAMS["NG"].contract_market_name
CFTC_CONTRACT_MARKET_CODE = COT_PARAMS["NG"].cftc_contract_market_code
OI_BASELINE = COT_PARAMS["NG"].oi_baseline
MM_NET_MIN = COT_PARAMS["NG"].mm_net_min
MM_NET_MAX = COT_PARAMS["NG"].mm_net_max


def generate(symbol: str = "NG") -> list[dict[str, Any]]:
    """Generate 100 weekly COT reports for `symbol`, ending the last Tuesday
    on or before 2026-05-10."""
    params = COT_PARAMS[symbol.upper()]
    scale = params.oi_baseline / NG_OI_BASELINE
    rng = np.random.default_rng(params.seed)

    # Find the last Tuesday on or before 2026-05-10 (a Sunday → 2026-05-05).
    end_date = date(2026, 5, 10)
    days_since_tuesday = (end_date.weekday() - 1) % 7  # Tuesday = weekday 1
    last_tuesday = end_date - timedelta(days=days_since_tuesday)
    assert last_tuesday.weekday() == 1, f"Expected Tuesday, got weekday {last_tuesday.weekday()}"

    # Build 100 Tuesdays in reverse then sort
    report_dates = []
    d = last_tuesday
    for _ in range(100):
        report_dates.append(d)
        d -= timedelta(weeks=1)
    report_dates.reverse()

    rows: list[dict[str, Any]] = []

    oi_baseline = params.oi_baseline
    oi_floor = oi_baseline * 4 // 7  # NG → 800,000
    mm_band = params.mm_net_max - params.mm_net_min
    mm_innovation_std = 15_000 * (mm_band / _NG_MM_BAND)

    # Managed-money net starts at the band midpoint (NG → 50,000).
    mm_net = (params.mm_net_min + params.mm_net_max) / 2.0

    n = len(report_dates)

    for i, report_date in enumerate(report_dates):
        release_date = report_date + timedelta(days=3)  # Friday

        # Open interest: baseline ± 10% slow drift + noise
        oi_drift = 0.10 * oi_baseline * np.sin(2 * np.pi * i / n)
        oi_noise = rng.normal(0, 10_000 * scale)
        open_interest = max(oi_floor, int(oi_baseline + oi_drift + oi_noise))

        # Managed-money net: AR(1) oscillator clamped to the symbol's band
        mm_innovation = rng.normal(0, mm_innovation_std)
        mm_net = 0.88 * mm_net + mm_innovation
        mm_net = float(np.clip(mm_net, params.mm_net_min, params.mm_net_max))

        mm_long = max(0, int(150_000 * scale + mm_net * 0.6))
        mm_short = max(0, int(150_000 * scale - mm_net * 0.4))

        # Producer net = inverse of MM with smoothing
        producer_net = -mm_net * 0.7
        producer_long  = max(0, int(400_000 * scale + producer_net * 0.4))
        producer_short = max(0, int(400_000 * scale - producer_net * 0.6))

        # Swap dealer: stable with small noise
        swap_long  = max(0, int(300_000 * scale + rng.normal(0, 8_000 * scale)))
        swap_short = max(0, int(280_000 * scale + rng.normal(0, 8_000 * scale)))

        # Other reportable: small
        other_long  = max(0, int(50_000 * scale + rng.normal(0, 3_000 * scale)))
        other_short = max(0, int(40_000 * scale + rng.normal(0, 3_000 * scale)))

        # Nonreportable: residual
        nr_long  = open_interest - producer_long  - swap_long  - mm_long  - other_long
        nr_short = open_interest - producer_short - swap_short - mm_short - other_short

        # Enforce non-negative nonreportable — adjust swap if needed
        if nr_long < 0:
            swap_long = max(0, swap_long + nr_long)  # reduce swap_long
            nr_long = open_interest - producer_long - swap_long - mm_long - other_long
            nr_long = max(0, nr_long)

        if nr_short < 0:
            swap_short = max(0, swap_short + nr_short)  # reduce swap_short
            nr_short = open_interest - producer_short - swap_short - mm_short - other_short
            nr_short = max(0, nr_short)

        rows.append({
            "report_date": report_date,
            "release_date": release_date,
            "contract_market_name": params.contract_market_name,
            "cftc_contract_market_code": params.cftc_contract_market_code,
            "producer_long": producer_long,
            "producer_short": producer_short,
            "swap_long": swap_long,
            "swap_short": swap_short,
            "managed_money_long": mm_long,
            "managed_money_short": mm_short,
            "other_reportable_long": other_long,
            "other_reportable_short": other_short,
            "nonreportable_long": nr_long,
            "nonreportable_short": nr_short,
            "open_interest_total": open_interest,
            "source": "mock",
        })

    return rows


if __name__ == "__main__":
    for sym in COT_PARAMS:
        rows = generate(sym)
        oi = rows[-1]["open_interest_total"]
        print(f"{sym}: {len(rows)} COT reports; last OI={oi:,}")
