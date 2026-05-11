"""
Generates weekly CFTC Commitments of Traders (disaggregated) reports.
100 weekly reports for natural gas futures.

Algorithm (from docs/MOCK_DATA_SPEC.md):
- Open interest baseline: ~1,400,000 contracts, slow drift ±10% over 2 years
- Managed money net oscillates between -150k and +250k, momentum-following (lags price by ~2 weeks)
  managed_money_long and managed_money_short derived from net + 150k long bias:
    managed_money_long = max(0, 150_000 + net * 0.6)
    managed_money_short = max(0, 150_000 - net * 0.4)
- Producer net is inverse of managed-money net with smoothing:
    producer_net = -managed_money_net * 0.7
    producer_long = max(0, 400_000 + producer_net * 0.4)
    producer_short = max(0, 400_000 - producer_net * 0.6)
- Swap dealer: relatively stable near swap_long=300k, swap_short=280k + small noise
- Other reportable: small, around 50k long, 40k short
- Nonreportable: residual to make categories sum to open_interest
  nonreportable_long = OI - producer_long - swap_long - managed_money_long - other_reportable_long
  nonreportable_short = OI - producer_short - swap_short - managed_money_short - other_reportable_short
  (enforce non-negative; if negative, cap at 0 and adjust swap to compensate)

report_date is Tuesday, release_date is the following Friday.
contract_market_name = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"
cftc_contract_market_code = "023651"

Return list[dict] with all cot_reports columns except id, fetched_at, managed_money_net (computed by DB).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CONTRACT_MARKET_NAME = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"
CFTC_CONTRACT_MARKET_CODE = "023651"

OI_BASELINE = 1_400_000
MM_NET_MIN = -150_000
MM_NET_MAX = 250_000


def generate() -> list[dict[str, Any]]:
    """Generate 100 weekly COT reports ending on the last Tuesday before 2026-05-10."""
    rng = np.random.default_rng(42)

    # Find the last Tuesday on or before 2026-05-10
    # 2026-05-10 is a Sunday (weekday=6), so last Tuesday is 2026-05-05
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

    # Simulate managed-money net as mean-reverting oscillator
    mm_net = 50_000.0  # starting value

    # OI slow drift: use a smooth sinusoidal drift over 2 years
    n = len(report_dates)

    for i, report_date in enumerate(report_dates):
        release_date = report_date + timedelta(days=3)  # Friday

        # Open interest: baseline ± 10% slow drift + noise
        oi_drift = 0.10 * OI_BASELINE * np.sin(2 * np.pi * i / n)
        oi_noise = rng.normal(0, 10_000)
        open_interest = max(800_000, int(OI_BASELINE + oi_drift + oi_noise))

        # Managed-money net: AR(1) oscillator clamped to [MM_NET_MIN, MM_NET_MAX]
        mm_innovation = rng.normal(0, 15_000)
        mm_net = 0.88 * mm_net + mm_innovation
        mm_net = float(np.clip(mm_net, MM_NET_MIN, MM_NET_MAX))

        mm_long = max(0, int(150_000 + mm_net * 0.6))
        mm_short = max(0, int(150_000 - mm_net * 0.4))

        # Producer net = inverse of MM with smoothing
        producer_net = -mm_net * 0.7
        producer_long  = max(0, int(400_000 + producer_net * 0.4))
        producer_short = max(0, int(400_000 - producer_net * 0.6))

        # Swap dealer: stable with small noise
        swap_long  = max(0, int(300_000 + rng.normal(0, 8_000)))
        swap_short = max(0, int(280_000 + rng.normal(0, 8_000)))

        # Other reportable: small
        other_long  = max(0, int(50_000 + rng.normal(0, 3_000)))
        other_short = max(0, int(40_000 + rng.normal(0, 3_000)))

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
            "contract_market_name": CONTRACT_MARKET_NAME,
            "cftc_contract_market_code": CFTC_CONTRACT_MARKET_CODE,
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
    rows = generate()
    print(f"Generated {len(rows)} COT reports")
    print(f"First: {rows[0]}")
    print(f"Last:  {rows[-1]}")
