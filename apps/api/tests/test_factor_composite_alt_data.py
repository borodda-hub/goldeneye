from apps.api.services.models.factor_composite import predict

CLOSES = [3.0 + i * 0.01 for i in range(20)]  # upward trending


def test_storage_bullish_signal():
    storage = {"delta_vs_consensus": -10.0}
    result = predict(CLOSES, "1d", latest_storage=storage)
    supporting_factors = [s["factor"] for s in result.supporting]
    assert "EIA storage delta vs consensus" in supporting_factors
    assert "latest_storage" in result.inputs_used


def test_cot_bullish_signal():
    cot = {"mm_net_delta": 5000.0}
    result = predict(CLOSES, "1d", latest_cot=cot)
    supporting_factors = [s["factor"] for s in result.supporting]
    assert "COT managed-money net delta" in supporting_factors
    assert "latest_cot" in result.inputs_used


def test_fallback_with_no_alt_data():
    result = predict(CLOSES, "1d", latest_storage=None, latest_cot=None)
    assert "closes" in result.inputs_used
    assert "latest_storage" not in result.inputs_used
    contradicting_factors = [c["factor"] for c in result.contradicting]
    assert "Missing alt-data" in contradicting_factors


def test_inputs_used_reflects_actual_data():
    storage = {"delta_vs_consensus": -5.0}
    cot = {"mm_net_delta": 1000.0}
    result = predict(CLOSES, "1d", latest_storage=storage, latest_cot=cot)
    assert "latest_storage" in result.inputs_used
    assert "latest_cot" in result.inputs_used


def test_both_sub_signals_agree_gives_medium_confidence():
    # Storage bearish + COT bearish + momentum downward → medium confidence
    closes_down = [3.5 - i * 0.01 for i in range(20)]
    storage = {"delta_vs_consensus": 15.0}  # bearish
    cot = {"mm_net_delta": -3000.0}  # bearish
    result = predict(closes_down, "1d", latest_storage=storage, latest_cot=cot)
    assert result.confidence == "medium"
    assert result.direction == "bearish"


# ── Phase 31a.0 — real-EIA shapes (no consensus survey) ───────────────────


def test_none_consensus_does_not_crash_and_falls_back():
    """TypeError regression: real EIA rows put delta_vs_consensus=None in the
    storage dict (EIA publishes no consensus survey). Pre-31a.0 this raised
    `float(None)`; it must degrade to the missing-alt-data branch instead."""
    result = predict(
        CLOSES, "1d", latest_storage={"delta_vs_consensus": None, "delta_vs_norm": None}
    )
    assert "latest_storage" not in result.inputs_used
    contradicting_factors = [c["factor"] for c in result.contradicting]
    assert "Missing alt-data" in contradicting_factors


def test_seasonal_norm_proxy_carries_storage_leg():
    """When consensus is absent, the seasonal-norm proxy powers the storage
    leg — labeled as the consensus-free proxy, never passed off as a survey."""
    storage = {"delta_vs_consensus": None, "delta_vs_norm": -20.0}
    result = predict(CLOSES, "1d", latest_storage=storage)
    assert "latest_storage" in result.inputs_used
    supporting_factors = [s["factor"] for s in result.supporting]
    assert (
        "EIA storage delta vs 5-year seasonal norm (consensus-free proxy)"
        in supporting_factors
    )


def test_consensus_preferred_over_proxy_when_both_present():
    storage = {"delta_vs_consensus": -10.0, "delta_vs_norm": 50.0}
    result = predict(CLOSES, "1d", latest_storage=storage)
    supporting_factors = [s["factor"] for s in result.supporting]
    assert "EIA storage delta vs consensus" in supporting_factors


def test_supporting_non_empty():
    result = predict(CLOSES, "1d")
    assert len(result.supporting) >= 1


def test_contradicting_non_empty():
    result = predict(CLOSES, "1d")
    assert len(result.contradicting) >= 1
