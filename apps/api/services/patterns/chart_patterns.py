"""Auto chart-pattern / auto-TA detection — swing-point geometry on OHLC bars.

Pure numpy (no scipy/TA dependency). Descriptive research output — support/
resistance levels, support/resistance trendlines, double tops/bottoms, and
head & shoulders (+ inverse) — each with a confidence in [0,1] and a
plain-English description in the cautious desk-analyst voice (marks inference,
no forbidden phrases). Observations, not trade signals.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _ts_iso(bar: dict[str, Any]) -> str:
    ts = bar["ts"]
    return ts.isoformat() if hasattr(ts, "isoformat") else str(ts)


def _swings(bars: list[dict[str, Any]], w: int = 3) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Swing highs / lows: a bar that is the window extreme and strictly beats
    its immediate neighbors (avoids plateaus)."""
    highs = np.array([float(b["high"]) for b in bars])
    lows = np.array([float(b["low"]) for b in bars])
    n = len(bars)
    sh: list[tuple[int, float]] = []
    sl: list[tuple[int, float]] = []
    for i in range(w, n - w):
        win_h = highs[i - w : i + w + 1]
        win_l = lows[i - w : i + w + 1]
        if highs[i] == win_h.max() and highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            sh.append((i, float(highs[i])))
        if lows[i] == win_l.min() and lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            sl.append((i, float(lows[i])))
    return sh, sl


def _levels(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    tol: float,
) -> list[dict[str, Any]]:
    """Cluster swing prices into support/resistance levels (>=2 touches)."""
    out: list[dict[str, Any]] = []
    for swings, kind in ((sh, "resistance"), (sl, "support")):
        prices = sorted(p for _, p in swings)
        cluster: list[float] = []
        for p in prices:
            if cluster and abs(p - (sum(cluster) / len(cluster))) <= tol:
                cluster.append(p)
            else:
                if len(cluster) >= 2:
                    out.append(
                        {"price": round(sum(cluster) / len(cluster), 4), "kind": kind, "touches": len(cluster)}
                    )
                cluster = [p]
        if len(cluster) >= 2:
            out.append(
                {"price": round(sum(cluster) / len(cluster), 4), "kind": kind, "touches": len(cluster)}
            )
    out.sort(key=lambda x: -x["touches"])
    return out[:6]


def _trendline(
    bars: list[dict[str, Any]], swings: list[tuple[int, float]], role: str
) -> dict[str, Any] | None:
    if len(swings) < 2:
        return None
    pts = swings[-4:]
    xs = np.array([i for i, _ in pts], dtype=float)
    ys = np.array([p for _, p in pts], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    i1 = int(pts[0][0])
    i2 = len(bars) - 1
    return {
        "role": role,
        "p1": {"ts": _ts_iso(bars[i1]), "price": round(float(slope * i1 + intercept), 4)},
        "p2": {"ts": _ts_iso(bars[i2]), "price": round(float(slope * i2 + intercept), 4)},
    }


def _similar(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def _pt(bars: list[dict[str, Any]], idx: int, price: float) -> dict[str, Any]:
    return {"ts": _ts_iso(bars[idx]), "price": round(float(price), 4)}


def detect_auto_ta(bars: list[dict[str, Any]], window: int = 3) -> dict[str, Any]:
    """Return {levels, trendlines, patterns}. Patterns scan the most recent
    swing structure and report the latest occurrence of each type."""
    if len(bars) < 4 * window + 4:
        return {"levels": [], "trendlines": [], "patterns": []}

    highs = np.array([float(b["high"]) for b in bars])
    lows = np.array([float(b["low"]) for b in bars])
    price_range = max(float(highs.max() - lows.min()), 1e-9)
    tol = price_range * 0.02

    sh, sl = _swings(bars, window)
    levels = _levels(sh, sl, price_range * 0.012)

    trendlines = [
        t
        for t in (
            _trendline(bars, sh, "resistance"),
            _trendline(bars, sl, "support"),
        )
        if t is not None
    ]

    patterns: list[dict[str, Any]] = []

    # ── Double top / bottom — two similar swing extremes with a reaction between.
    if len(sh) >= 2:
        (i1, p1), (i2, p2) = sh[-2], sh[-1]
        valley = [p for i, p in sl if i1 < i < i2]
        if _similar(p1, p2, tol) and valley:
            neck = min(valley)
            patterns.append(
                {
                    "name": "Double Top",
                    "direction": "bearish",
                    "points": [_pt(bars, i1, p1), _pt(bars, i2, p2)],
                    "neckline": round(float(neck), 4),
                    "confidence": round(0.6 - abs(p1 - p2) / tol * 0.2, 2),
                    "description": "Two peaks at a similar level with a dip between — reads as resistance holding; a tentative bearish reversal if price closes below the intervening low.",
                }
            )
    if len(sl) >= 2:
        (i1, p1), (i2, p2) = sl[-2], sl[-1]
        peak = [p for i, p in sh if i1 < i < i2]
        if _similar(p1, p2, tol) and peak:
            neck = max(peak)
            patterns.append(
                {
                    "name": "Double Bottom",
                    "direction": "bullish",
                    "points": [_pt(bars, i1, p1), _pt(bars, i2, p2)],
                    "neckline": round(float(neck), 4),
                    "confidence": round(0.6 - abs(p1 - p2) / tol * 0.2, 2),
                    "description": "Two troughs at a similar level with a bounce between — reads as support holding; a tentative bullish reversal if price closes above the intervening high.",
                }
            )

    # ── Head & shoulders — three swing highs, middle highest, shoulders level.
    if len(sh) >= 3:
        (ia, pa), (ib, pb), (ic, pc) = sh[-3], sh[-2], sh[-1]
        if pb > pa and pb > pc and _similar(pa, pc, tol * 1.5):
            patterns.append(
                {
                    "name": "Head & Shoulders",
                    "direction": "bearish",
                    "points": [_pt(bars, ia, pa), _pt(bars, ib, pb), _pt(bars, ic, pc)],
                    "neckline": round(float(min(p for i, p in sl if ia < i < ic) if any(ia < i < ic for i, _ in sl) else min(pa, pc)), 4),
                    "confidence": 0.6,
                    "description": "A higher peak flanked by two lower, roughly level peaks — a classic topping shape; reads as bearish, with the caveat it needs a neckline break to confirm.",
                }
            )
    if len(sl) >= 3:
        (ia, pa), (ib, pb), (ic, pc) = sl[-3], sl[-2], sl[-1]
        if pb < pa and pb < pc and _similar(pa, pc, tol * 1.5):
            patterns.append(
                {
                    "name": "Inverse Head & Shoulders",
                    "direction": "bullish",
                    "points": [_pt(bars, ia, pa), _pt(bars, ib, pb), _pt(bars, ic, pc)],
                    "neckline": round(float(max(p for i, p in sh if ia < i < ic) if any(ia < i < ic for i, _ in sh) else max(pa, pc)), 4),
                    "confidence": 0.6,
                    "description": "A lower trough flanked by two higher, roughly level troughs — a classic basing shape; reads as bullish pending a neckline break.",
                }
            )

    return {"levels": levels, "trendlines": trendlines, "patterns": patterns}
