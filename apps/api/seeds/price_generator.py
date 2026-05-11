"""
Generates deterministic OHLCV price bars for the NGM26 front-month contract.

Returns two result types from generate():
  - bars: list of dicts for price_bars table (contract_code, resolution, ts, open, high, low, close, volume, source)
  - snapshots: list of dicts for futures_curve_snapshots (instrument_symbol, ts, curve)

Algorithm (from docs/MOCK_DATA_SPEC.md):
- 730 trading days back from 2026-05-10, daily resolution "1d"
- 1-minute bars for the most recent 14 trading days, resolution "1m"
- Regime-switching GBM with 4 states:
    compressed:  sigma=0.18, drift=0.0
    normal:      sigma=0.32, drift=0.0003
    elevated:    sigma=0.55, drift=0.0006
    crisis:      sigma=0.90, drift=0.0
  Markov chain transition so time in regime is roughly 25% / 50% / 20% / 5%
- Starting price: 3.20
- Open = prev_close + small overnight gap (N(0, 0.003))
- High = max(open, close) * (1 + |epsilon| * 0.3)  where epsilon ~ half-normal(sigma_regime)
- Low  = min(open, close) * (1 - |epsilon| * 0.3)
  Enforce: high >= max(open,close), low <= min(open,close), high > low
- Volume = base_volume * (1 + 2*abs(daily_return)) where base_volume ~ 400_000 + noise
  Weekly seasonality: Mon/Thu factor 1.2, other days factor 0.9
- Seasonality overlay: gentle cosine that raises winter prices ~5% and softens summer ~3%
- Daily curve snapshot: 12 monthly contracts starting at NGM26, contango slope
  of ~0.02/month normally, occasionally ~-0.005/month (backwardation during cold stretches)

For 1-minute bars: generate intraday path from open to close using same GBM at 1min resolution,
  aggregate correctly so minute OHLC is consistent with daily.

Return format from generate() -> dict:
  {
    "bars": [{"contract_code": "NGM26", "resolution": "1d", "ts": datetime, "open": float,
              "high": float, "low": float, "close": float, "volume": int, "source": "mock"}, ...],
    "snapshots": [{"instrument_symbol": "NG", "ts": datetime,
                   "curve": [{"contract_code": str, "expiry": str, "mid_price": float}]}, ...]
  }
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── constants ──────────────────────────────────────────────────────────────────

CONTRACT_CODE = "NGM26"
INSTRUMENT_SYMBOL = "NG"
START_PRICE = 3.20
TODAY = datetime(2026, 5, 10)

# Regime parameters: (sigma_annual, drift_annual)
# Sigma is annual vol; we convert to daily/intraday as needed.
REGIMES = {
    0: {"name": "compressed", "sigma": 0.18, "drift": 0.000},
    1: {"name": "normal",     "sigma": 0.32, "drift": 0.0003},
    2: {"name": "elevated",   "sigma": 0.55, "drift": 0.0006},
    3: {"name": "crisis",     "sigma": 0.90, "drift": 0.000},
}

# Markov chain transition matrix calibrated for ~25/50/20/5% steady state
# Rows: current regime, columns: next regime
TRANSITION_MATRIX = np.array([
    [0.93, 0.06, 0.01, 0.00],  # compressed
    [0.02, 0.93, 0.04, 0.01],  # normal
    [0.02, 0.10, 0.86, 0.02],  # elevated
    [0.02, 0.15, 0.13, 0.70],  # crisis
])

# Month letters for futures contracts
MONTH_LETTERS = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z",
}


def _seasonal_factor(dt: datetime) -> float:
    """Cosine seasonality: ~+5% in winter, ~-3% in summer."""
    doy = dt.timetuple().tm_yday
    # peak around Jan 1 (doy=1), trough around July 4 (doy ~185)
    # Using doy_peak = 1 → offset so winter is high
    factor = 0.04 * math.cos(2 * math.pi * (doy - 1) / 365)
    return factor  # range approx [-0.04, +0.04]


def _regime_sigma_daily(regime: int) -> float:
    """Convert annual sigma to daily sigma (252 trading days)."""
    return REGIMES[regime]["sigma"] / math.sqrt(252)


def _regime_sigma_minute(regime: int) -> float:
    """Convert annual sigma to per-minute sigma (252 * 390 minutes)."""
    return REGIMES[regime]["sigma"] / math.sqrt(252 * 390)


def _next_regime(current: int, rng: np.random.Generator) -> int:
    row = TRANSITION_MATRIX[current]
    return int(rng.choice(4, p=row))


def _get_trading_days(n: int, end: datetime) -> pd.DatetimeIndex:
    """Return the last n business days up to and including end."""
    end_ts = pd.Timestamp(end.date())
    return pd.bdate_range(end=end_ts, periods=n)


def _build_curve_snapshot(
    ts: datetime,
    front_price: float,
    rng: np.random.Generator,
    is_cold_stretch: bool,
) -> dict[str, Any]:
    """Build a 12-contract futures curve snapshot."""
    if is_cold_stretch:
        slope = -0.005 + rng.normal(0, 0.002)
    else:
        slope = 0.02 + rng.normal(0, 0.005)

    curve = []
    # Start from the month that contains ts, build 12 forward contracts
    start_month = ts.month
    start_year = ts.year

    for i in range(12):
        month = (start_month + i - 1) % 12 + 1
        year = start_year + (start_month + i - 1) // 12
        letter = MONTH_LETTERS[month]
        code = f"NG{letter}{str(year)[2:]}"

        # Expiry: approximately last business day of the month before delivery
        # Use last business day of the prior month
        expiry_month = month - 1 if month > 1 else 12
        expiry_year = year if month > 1 else year - 1
        # Last day of expiry_month
        if expiry_month == 12:
            last_day = datetime(expiry_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(expiry_year, expiry_month + 1, 1) - timedelta(days=1)
        # Walk back to last business day
        while last_day.weekday() >= 5:
            last_day -= timedelta(days=1)
        expiry_str = last_day.strftime("%Y-%m-%d")

        mid_price = round(front_price + slope * i + rng.normal(0, 0.005), 4)
        mid_price = max(mid_price, 0.50)  # floor
        curve.append({
            "contract_code": code,
            "expiry": expiry_str,
            "mid_price": mid_price,
        })

    return {
        "instrument_symbol": INSTRUMENT_SYMBOL,
        "ts": ts,
        "curve": curve,
    }


def generate() -> dict[str, list[Any]]:
    """Generate price bars and curve snapshots deterministically."""
    rng = np.random.default_rng(42)

    # ── Build trading day calendar ──────────────────────────────────────────
    trading_days = _get_trading_days(730, TODAY)

    # ── Simulate regime and price path ─────────────────────────────────────
    n = len(trading_days)
    regime = 1  # start in normal
    price = START_PRICE

    bars: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []

    prev_close = price

    for idx, ts_pd in enumerate(trading_days):
        ts = ts_pd.to_pydatetime()
        # Full daily datetime at market open time
        ts_bar = datetime(ts.year, ts.month, ts.day, 9, 30, 0)

        # Regime transition
        regime = _next_regime(regime, rng)
        sigma_d = _regime_sigma_daily(regime)
        drift_d = REGIMES[regime]["drift"]

        # Seasonality overlay on close price
        season = _seasonal_factor(ts)

        # Open = prev_close + overnight gap
        overnight_gap = rng.normal(0, 0.003) * prev_close
        open_price = max(prev_close + overnight_gap, 0.10)

        # GBM step for close
        z = rng.normal(0, 1)
        log_return = drift_d + sigma_d * z
        # Apply seasonality as a gentle overlay (1% of seasonal factor per day)
        log_return += season * 0.005
        close_price = max(open_price * math.exp(log_return), 0.10)

        # High / Low
        eps_h = abs(rng.normal(0, sigma_d))
        eps_l = abs(rng.normal(0, sigma_d))
        high_raw = max(open_price, close_price) * (1.0 + eps_h * 0.3)
        low_raw  = min(open_price, close_price) * (1.0 - eps_l * 0.3)

        high_price = max(high_raw, open_price, close_price)
        low_price  = min(low_raw, open_price, close_price)
        if high_price <= low_price:
            high_price = low_price + 0.001

        # Volume
        daily_return = abs(log_return)
        base_vol = 400_000 + rng.normal(0, 20_000)
        weekday = ts.weekday()  # 0=Mon, 3=Thu
        if weekday in (0, 3):
            vol_factor = 1.2
        else:
            vol_factor = 0.9
        volume = max(1, int(base_vol * vol_factor * (1.0 + 2.0 * daily_return)))

        # Round then re-enforce invariants in case rounding causes violations
        r_open  = round(open_price, 4)
        r_close = round(close_price, 4)
        r_high  = round(high_price, 4)
        r_low   = round(low_price, 4)
        r_high  = max(r_high, r_open, r_close)
        r_low   = min(r_low, r_open, r_close)
        if r_high <= r_low:
            r_high = r_low + 0.0001

        bar: dict[str, Any] = {
            "contract_code": CONTRACT_CODE,
            "resolution": "1d",
            "ts": ts_bar,
            "open": r_open,
            "high": r_high,
            "low": r_low,
            "close": r_close,
            "volume": volume,
            "source": "mock",
        }
        bars.append(bar)

        # Determine if cold stretch for curve shape (elevated or crisis regime in winter)
        doy = ts.timetuple().tm_yday
        is_cold = regime >= 2 and (doy < 90 or doy > 300)

        snapshot = _build_curve_snapshot(
            ts=datetime(ts.year, ts.month, ts.day, 16, 0, 0),
            front_price=close_price,
            rng=rng,
            is_cold_stretch=is_cold,
        )
        snapshots.append(snapshot)

        prev_close = close_price

    # ── Generate 1-minute bars for last 14 trading days ────────────────────
    last_14 = trading_days[-14:]
    # Map daily bar data by date for reference
    daily_by_date = {
        b["ts"].date(): b
        for b in bars
        if b["ts"].date() in {d.date() for d in last_14}
    }

    # Re-run a fresh rng seeded deterministically for intraday
    rng_intra = np.random.default_rng(142)  # different seed but deterministic
    regime_intra = 1

    for ts_pd in last_14:
        ts = ts_pd.to_pydatetime()
        day_bar = daily_by_date.get(ts.date())
        if day_bar is None:
            continue

        day_open  = day_bar["open"]
        day_close = day_bar["close"]
        day_high  = day_bar["high"]
        day_low   = day_bar["low"]

        # Generate 390-step GBM from open to close
        regime_intra = _next_regime(regime_intra, rng_intra)
        sigma_m = _regime_sigma_minute(regime_intra)
        drift_m = REGIMES[regime_intra]["drift"] / (252 * 390)

        # We want the final price to land exactly on day_close
        # Use bridge: generate raw path, then scale to match
        n_minutes = 390
        zs = rng_intra.normal(0, 1, n_minutes)
        increments = drift_m + sigma_m * zs
        # Force the path to end at day_close by adjusting the last step
        raw_path = np.exp(np.cumsum(increments))
        # Scale so first point starts at day_open and last ends at day_close
        scale = day_close / (day_open * raw_path[-1])
        prices = day_open * raw_path * scale

        # Clip to ensure prices stay positive
        prices = np.maximum(prices, 0.01)

        # Build minute bars from the price path
        bar_start = datetime(ts.year, ts.month, ts.day, 9, 30, 0)
        for m in range(n_minutes):
            minute_ts = bar_start + timedelta(minutes=m)
            p = prices[m]
            if m == 0:
                m_open = day_open
            else:
                m_open = prices[m - 1]

            m_close = p
            m_high = max(m_open, m_close) * (1.0 + abs(rng_intra.normal(0, sigma_m * 0.3)))
            m_low  = min(m_open, m_close) * (1.0 - abs(rng_intra.normal(0, sigma_m * 0.3)))
            m_high = max(m_high, m_open, m_close)
            m_low  = min(m_low, m_open, m_close)
            if m_high <= m_low:
                m_high = m_low + 0.0001

            m_vol = max(1, int(rng_intra.integers(500, 2000)))

            # Round then re-enforce to prevent invariant violations from rounding
            rm_open  = round(float(m_open), 4)
            rm_close = round(float(m_close), 4)
            rm_high  = round(float(m_high), 4)
            rm_low   = round(float(m_low), 4)
            rm_high  = max(rm_high, rm_open, rm_close)
            rm_low   = min(rm_low, rm_open, rm_close)
            if rm_high <= rm_low:
                rm_high = rm_low + 0.0001

            bars.append({
                "contract_code": CONTRACT_CODE,
                "resolution": "1m",
                "ts": minute_ts,
                "open": rm_open,
                "high": rm_high,
                "low": rm_low,
                "close": rm_close,
                "volume": m_vol,
                "source": "mock",
            })

    return {"bars": bars, "snapshots": snapshots}


if __name__ == "__main__":
    result = generate()
    daily = [b for b in result["bars"] if b["resolution"] == "1d"]
    minute = [b for b in result["bars"] if b["resolution"] == "1m"]
    print(f"Daily bars: {len(daily)}")
    print(f"1-minute bars: {len(minute)}")
    print(f"Curve snapshots: {len(result['snapshots'])}")
    print(f"First daily bar: {daily[0]}")
    print(f"Last daily bar: {daily[-1]}")
