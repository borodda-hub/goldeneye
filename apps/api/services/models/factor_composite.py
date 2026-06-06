"""
Factor Composite — a transparent, rules-based blend of alt-data signals
(EIA storage surprise, COT managed-money delta) and short-term price momentum,
combined by weighted voting. Consumes alt-data when available and falls back to
price momentum only when it's missing.

This is deliberately NOT a trained machine-learning model: every weight and
threshold below is hand-set and auditable. A learned model replaces it in a
later phase; until then the output carries an explicit "not a trained model"
disclaimer so nothing here overstates what it is.
"""
from __future__ import annotations


def predict(
    closes: list[float],
    horizon: str = "1d",
    latest_storage: dict | None = None,
    latest_cot: dict | None = None,
) -> "ForecastResult":
    from apps.api.services.models.moving_average_directional import ForecastResult

    # Sub-signal votes: each (direction, weight)
    sub_votes: list[tuple[str, float]] = []
    inputs_used: list[str] = ["closes"]
    supporting: list[dict] = []
    contradicting: list[dict] = [
        {
            "factor": "Not a trained model",
            "weight": 0.8,
            "note": "Rules-based composite of storage, positioning, and momentum "
            "signals — every weight is hand-set, not learned. A trained model "
            "replaces it in a later phase.",
        }
    ]

    # Storage sub-signal (weight 0.4)
    if latest_storage is not None and "delta_vs_consensus" in latest_storage:
        delta = float(latest_storage["delta_vs_consensus"])
        if delta < 0:
            sub_dir = "bullish"
            note = f"EIA storage delta vs consensus: {delta:.1f} Bcf (smaller build / larger draw → bullish)."
        elif delta > 0:
            sub_dir = "bearish"
            note = f"EIA storage delta vs consensus: {delta:.1f} Bcf (larger build → bearish)."
        else:
            sub_dir = "neutral"
            note = "EIA storage delta vs consensus: 0 Bcf (in line with expectations)."
        sub_votes.append((sub_dir, 0.4))
        supporting.append({"factor": "EIA storage delta vs consensus", "weight": 0.4, "note": note})
        inputs_used.append("latest_storage")
    else:
        contradicting.append(
            {
                "factor": "Missing alt-data",
                "weight": 0.5,
                "note": "Storage and/or COT context unavailable; falling back to price momentum only.",
            }
        )

    # COT sub-signal (weight 0.3)
    if latest_cot is not None and "mm_net_delta" in latest_cot:
        mm_delta = float(latest_cot["mm_net_delta"])
        if mm_delta > 0:
            sub_dir = "bullish"
            note = f"Managed-money net position WoW change: +{mm_delta:.0f} contracts (getting longer → bullish)."
        elif mm_delta < 0:
            sub_dir = "bearish"
            note = f"Managed-money net position WoW change: {mm_delta:.0f} contracts (getting shorter → bearish)."
        else:
            sub_dir = "neutral"
            note = "Managed-money net position unchanged WoW."
        sub_votes.append((sub_dir, 0.3))
        supporting.append({"factor": "COT managed-money net delta", "weight": 0.3, "note": note})
        inputs_used.append("latest_cot")

    # Momentum sub-signal (weight 0.3)
    recent = closes[-5:] if len(closes) >= 5 else closes
    older = closes[-10:-5] if len(closes) >= 10 else closes[: len(closes) // 2]
    if not recent or not older:
        mom_dir = "neutral"
        mom_note = "Insufficient price history for momentum signal."
    else:
        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older)
        if recent_mean > older_mean:
            mom_dir = "bullish"
            mom_note = "5-day mean above prior 5-day mean (short-term upward momentum)."
        else:
            mom_dir = "bearish"
            mom_note = "5-day mean below prior 5-day mean (short-term downward momentum)."
    sub_votes.append((mom_dir, 0.3))
    supporting.append({"factor": "Short-term price momentum", "weight": 0.3, "note": mom_note})

    # Ensure supporting is non-empty (already guaranteed by momentum above)

    # Aggregate weighted votes
    totals: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    for sub_dir, w in sub_votes:
        d = sub_dir if sub_dir in totals else "neutral"
        totals[d] += w

    max_w = max(totals.values())
    winners = [d for d, w in totals.items() if w == max_w]
    direction = winners[0] if len(winners) == 1 else "neutral"

    # Agreement: medium if at least 2 sub-signals agree, low otherwise
    agreeing = sum(1 for sub_dir, _ in sub_votes if sub_dir == direction)
    confidence = "medium" if agreeing >= 2 else "low"

    expected_pct = 0.005 if direction == "bullish" else (-0.005 if direction == "bearish" else 0.0)

    return ForecastResult(
        model_name="factor_composite",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=expected_pct,
        range_low_pct=-0.02,
        range_high_pct=0.02,
        vol_regime=None,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=inputs_used,
    )
