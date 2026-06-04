"""Candlestick pattern detection — deterministic geometry on OHLC bars.

~19 widely-recognized patterns. Each detection is a *descriptive observation*
of recent price action (not a trade signal): it carries a direction
(bullish/bearish/neutral), a heuristic strength in [0,1], and a plain-English
meaning written in the desk-analyst voice (marks inference, no forbidden
phrases). Trend-context patterns (hammer vs hanging man, etc.) use a short
prior-trend check.

Pure Python — no third-party TA dependency, so it stays deterministic and
trivially unit-testable on seeded bars.
"""
from __future__ import annotations

from typing import Any

# Per-bar geometry: (open, high, low, close, range, body, upper_shadow, lower_shadow)
_Metrics = tuple[float, float, float, float, float, float, float, float]


def _metrics(bar: dict[str, Any]) -> _Metrics:
    o = float(bar["open"])
    h = float(bar["high"])
    low = float(bar["low"])
    c = float(bar["close"])
    rng = max(h - low, 1e-9)
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - low
    return o, h, low, c, rng, body, upper, lower


def _ts_iso(bar: dict[str, Any]) -> str:
    ts = bar["ts"]
    return ts.isoformat() if hasattr(ts, "isoformat") else str(ts)


def detect_patterns(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candlestick-pattern detections, newest-relevant order preserved.

    Each item: {ts, code, name, direction, strength, meaning}. A single bar may
    anchor more than one pattern.
    """
    n = len(bars)
    if n < 3:
        return []

    m = [_metrics(b) for b in bars]
    closes = [x[3] for x in m]
    bodies = [x[5] for x in m]
    avg_body = (sum(bodies) / n) or 1e-9

    def trend_down(i: int, look: int = 3) -> bool:
        j = i - 1
        return j - look >= 0 and closes[j] < closes[j - look]

    def trend_up(i: int, look: int = 3) -> bool:
        j = i - 1
        return j - look >= 0 and closes[j] > closes[j - look]

    out: list[dict[str, Any]] = []

    def emit(i: int, code: str, name: str, direction: str, strength: float, meaning: str) -> None:
        out.append(
            {
                "ts": _ts_iso(bars[i]),
                "code": code,
                "name": name,
                "direction": direction,
                "strength": round(float(strength), 2),
                "meaning": meaning,
            }
        )

    for i in range(n):
        o, h, low, c, rng, body, upper, lower = m[i]
        is_bull = c > o
        is_bear = c < o

        # ── Doji family (very small body) ──────────────────────────────────
        if body <= 0.08 * rng:
            if lower > 2 * body and upper < body:
                emit(i, "DDJ", "Dragonfly Doji", "bullish", 0.4,
                     "Open and close sit near the high after a long lower wick — sellers were rejected; reads as tentatively bullish.")
            elif upper > 2 * body and lower < body:
                emit(i, "GDJ", "Gravestone Doji", "bearish", 0.4,
                     "Open and close sit near the low after a long upper wick — buyers were rejected; reads as tentatively bearish.")
            else:
                emit(i, "DJI", "Doji", "neutral", 0.3,
                     "Open and close are nearly equal — suggests indecision between buyers and sellers.")
            continue

        small_body = body <= 0.34 * rng
        long_lower = lower >= 2 * body
        long_upper = upper >= 2 * body

        # ── Single-bar reversal/continuation shapes ────────────────────────
        if small_body and long_lower and upper <= 0.6 * body:
            if trend_down(i):
                emit(i, "HMR", "Hammer", "bullish", 0.55,
                     "A small body with a long lower wick after a decline — suggests buyers absorbed selling; a tentative bullish reversal, with the caveat it needs confirmation.")
            elif trend_up(i):
                emit(i, "HGM", "Hanging Man", "bearish", 0.5,
                     "A small body with a long lower wick after an advance — reads as a tentative bearish reversal; however, confirmation is required.")
        if small_body and long_upper and lower <= 0.6 * body:
            if trend_down(i):
                emit(i, "IHM", "Inverted Hammer", "bullish", 0.5,
                     "A small body with a long upper wick after a decline — suggests buyers tested higher; a tentative bullish reversal pending confirmation.")
            elif trend_up(i):
                emit(i, "SHS", "Shooting Star", "bearish", 0.55,
                     "A small body with a long upper wick after an advance — sellers rejected the highs; reads as a tentative bearish reversal.")
        if upper <= 0.05 * rng and lower <= 0.05 * rng and body >= 0.9 * rng:
            emit(i, "MAR", "Marubozu", "bullish" if is_bull else "bearish", 0.45,
                 "A full body with negligible wicks — one side controlled the session; consistent with continuation of the prevailing move.")
        if small_body and upper >= body and lower >= body and body > 0.08 * rng:
            emit(i, "SPT", "Spinning Top", "neutral", 0.3,
                 "A small body with wicks on both sides — suggests a balance of buyers and sellers and waning momentum.")

        # ── Two-bar patterns ───────────────────────────────────────────────
        if i >= 1:
            po, ph, plow, pc, prng, pbody, _pu, _pl = m[i - 1]
            prev_bull = pc > po
            prev_bear = pc < po
            body_hi, body_lo = max(o, c), min(o, c)
            pbody_hi, pbody_lo = max(po, pc), min(po, pc)

            if prev_bear and is_bull and o <= pc and c >= po and body > pbody:
                emit(i, "BEN", "Bullish Engulfing", "bullish", 0.7,
                     "An up-bar fully covers the prior down-bar — suggests buyers seized control; a fairly strong bullish reversal, less convincingly so without rising volume.")
            if prev_bull and is_bear and o >= pc and c <= po and body > pbody:
                emit(i, "BRE", "Bearish Engulfing", "bearish", 0.7,
                     "A down-bar fully covers the prior up-bar — suggests sellers seized control; a fairly strong bearish reversal, with the caveat that volume should confirm.")
            if (
                pbody >= avg_body
                and body < pbody * 0.6
                and body_hi <= pbody_hi
                and body_lo >= pbody_lo
            ):
                if prev_bear and is_bull:
                    emit(i, "BHA", "Bullish Harami", "bullish", 0.5,
                         "A small up-bar sits inside the prior large down-bar — suggests selling momentum is stalling; reads as a tentative bullish turn.")
                elif prev_bull and is_bear:
                    emit(i, "BRH", "Bearish Harami", "bearish", 0.5,
                         "A small down-bar sits inside the prior large up-bar — suggests buying momentum is stalling; reads as a tentative bearish turn.")
            if prev_bear and is_bull and o < pc and c > (po + pc) / 2 and c < po:
                emit(i, "PRC", "Piercing Line", "bullish", 0.55,
                     "Price opened below the prior close then closed back above its midpoint — suggests buyers stepped in; a tentative bullish reversal.")
            if prev_bull and is_bear and o > pc and c < (po + pc) / 2 and c > po:
                emit(i, "DCC", "Dark Cloud Cover", "bearish", 0.55,
                     "Price opened above the prior close then closed below its midpoint — suggests sellers stepped in; a tentative bearish reversal.")

        # ── Three-bar patterns ─────────────────────────────────────────────
        if i >= 2:
            o2, _h2, _l2, c2, _r2, b2, _u2, _l2b = m[i - 2]
            o1, _h1, _l1, c1, r1, b1, _u1, _l1b = m[i - 1]
            mid2 = (o2 + c2) / 2
            star = b1 <= 0.4 * r1
            if c2 < o2 and b2 >= avg_body and star and is_bull and c > mid2:
                emit(i, "MST", "Morning Star", "bullish", 0.65,
                     "A down-bar, a small-bodied pause, then a strong up-bar closing into the first body — reads as a bullish reversal, with the caveat it needs follow-through.")
            if c2 > o2 and b2 >= avg_body and star and is_bear and c < mid2:
                emit(i, "EST", "Evening Star", "bearish", 0.65,
                     "An up-bar, a small-bodied pause, then a strong down-bar closing into the first body — reads as a bearish reversal pending follow-through.")
            prev2_bull = c2 > o2 and c1 > o1
            if (
                prev2_bull and is_bull
                and c1 > c2 and c > c1
                and o1 > min(o2, c2) and o > min(o1, c1)
            ):
                emit(i, "TWS", "Three White Soldiers", "bullish", 0.6,
                     "Three rising up-bars each opening within the prior body — suggests steady, broad buying; consistent with a bullish trend.")
            prev2_bear = c2 < o2 and c1 < o1
            if (
                prev2_bear and is_bear
                and c1 < c2 and c < c1
                and o1 < max(o2, c2) and o < max(o1, c1)
            ):
                emit(i, "TBC", "Three Black Crows", "bearish", 0.6,
                     "Three falling down-bars each opening within the prior body — suggests steady, broad selling; consistent with a bearish trend.")

    return out
