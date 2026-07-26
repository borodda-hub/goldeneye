"""The validation ledger as structured data (Phase A3).

The single content source for the "How We Validate" page. Each row mirrors
one row of `docs/MODEL_DILIGENCE.md` (the claims SOT) — hand-curated
because the rows are editorial judgments, but STRUCTURALLY LOCKED to the
doc by `tests/test_validation_ledger.py`:

- every row's `doc_anchor` must appear on exactly one line of the doc,
- that line must contain the row's `doc_marker` (verdict consistency),
- row count must equal the doc's ledger-table row count (parity).

Editing the doc without this file (or vice versa) fails CI in the fast
suite — the page cannot drift from the ledger, in either direction.

Per the non-negotiable rule, every row carries `provenance`. Rows are
returned in display order: the validated edge first, the no-edge family
next (failures are first-class content, never buried), then promising /
parked, then collecting archives, then methodology.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

VerdictKind = Literal[
    "edge",  # validated, real-OOS, holds
    "no_edge",  # tested on real data; claim honestly retired
    "promising",  # passed a pre-registered tie-breaker; not crowned
    "insufficient",  # pre-registered power rule bound / premise absent
    "collecting",  # archive accumulating; unvalidatable yet, no claim
    "benched",  # failed its gate vs an incumbent; code kept, not wired
    "methodology",  # a measurement/honesty mechanism, not a predictive claim
    "unvalidated",  # hand-set configuration carrying no claim
]


@dataclass(frozen=True)
class LedgerRow:
    key: str
    claim: str
    verdict: VerdictKind
    provenance: str  # synthetic | real-OOS | real-in-sample | methodology | collecting
    summary: str  # one line, plain language, no forbidden phrases
    evidence: str  # harness · sample-size note
    rerun: str | None  # the one-command reproduction, when one exists
    gate_ref: str  # where the gate/pre-registration lives
    updated: str  # YYYY-MM-DD of the latest verdict
    doc_anchor: str  # unique substring of the MODEL_DILIGENCE.md row (drift lock)
    doc_marker: str  # substring that must co-occur on that line (verdict lock)


ROWS: tuple[LedgerRow, ...] = (
    # ── The validated edge ────────────────────────────────────────────────
    LedgerRow(
        key="vol_band_80",
        claim="The 80% price-range band is calibrated",
        verdict="edge",
        provenance="real-OOS",
        summary="Walk-forward coverage holds at 78-81% across all six "
        "commodities on ~10y of real daily prices.",
        evidence="validate_vol_real · 6/6 commodities @1w · n_eff≈497",
        rerun="uv run --directory apps/api python -m seeds.validate_vol_real",
        gate_ref="tests/test_vol_range.py (locked regression)",
        updated="2026-06-07",
        doc_anchor="80% band** is calibrated",
        doc_marker="real-OOS** ✅",
    ),
    LedgerRow(
        key="vol_band_95",
        claim="The 95% band reaches nominal coverage (fat tails)",
        verdict="edge",
        provenance="real-OOS",
        summary="Empirical fat-tail quantiles (Phase 30c) lift real-data 95% "
        "coverage to 93-95%.",
        evidence="validate_vol_real · post-30c quantiles",
        rerun="uv run --directory apps/api python -m seeds.validate_vol_real",
        gate_ref="tests/test_vol_range.py (locked regression)",
        updated="2026-06-07",
        doc_anchor="95% band** is calibrated",
        doc_marker="real-OOS** ✅",
    ),
    LedgerRow(
        key="vol_fwd_info",
        claim="The vol forecast carries forward-looking information",
        verdict="edge",
        provenance="real-OOS",
        summary="Forecast vol correlates 0.44-0.59 with realized forward vol "
        "at 1w — stronger on real data than on the synthetic seed.",
        evidence="forecast_vol_correlation · n_eff≈497",
        rerun="uv run --directory apps/api python -m seeds.validate_vol_real",
        gate_ref="tests/test_vol_range.py (locked regression)",
        updated="2026-06-07",
        doc_anchor="forward-vol info",
        doc_marker="real-OOS** ✅",
    ),
    LedgerRow(
        key="har_log_default",
        claim="log-HAR beats EWMA as the vol point-forecast (now the default)",
        verdict="edge",
        provenance="real-OOS",
        summary="Beats the EWMA incumbent on out-of-sample R² in 5/6 "
        "commodities at 1w; the default swap was re-validated skill-neutral.",
        evidence="estimator_skill · ~10y real, 6 commodities",
        rerun="uv run --directory apps/api python -m seeds.validate_estimator_30b",
        gate_ref="docs/MODEL_DILIGENCE.md §ledger (30b gate)",
        updated="2026-06-08",
        doc_anchor="log-HAR beats EWMA",
        doc_marker="real-OOS** ✅",
    ),
    # ── Direction: tested, no edge — published, not buried ────────────────
    LedgerRow(
        key="direction_price_only",
        claim="Price-only directional models (MA, Holt)",
        verdict="no_edge",
        provenance="real-OOS",
        summary="Decisive accuracy 45-57%, below a drift-aware naive "
        "baseline in all 36 commodity/horizon cells. No confidence gradient.",
        evidence="validate_direction_real + validate_engine_oos · 36/36 cells",
        rerun="uv run --directory apps/api python -m seeds.validate_engine_oos",
        gate_ref="docs/MODEL_DILIGENCE.md §ledger",
        updated="2026-06-07",
        doc_anchor="moving_average_directional`, `holt_trend`",
        doc_marker="No edge",
    ),
    LedgerRow(
        key="factor_alt_data",
        claim="factor_composite with real COT + storage features",
        verdict="no_edge",
        provenance="real-OOS",
        summary="Real alt-data made the model worse, not better: ~6 SE worse "
        "than its own price-only variant on 2,958 non-overlapping weekly "
        "decisions. The gate failed; the claim is retired.",
        evidence="validate_engine_oos --alt-only · n=2,958 @1w (n_eff=n)",
        rerun="uv run --directory apps/api python -m seeds.validate_engine_oos --alt-only",
        gate_ref="docs/PHASE_31_PLAN.md §31b (gate pre-registered before the run)",
        updated="2026-07-25",
        doc_anchor="alt-data legs",
        doc_marker="FAIL on the pre-registered gate",
    ),
    LedgerRow(
        key="logreg_directional",
        claim="logreg_directional (trained, price-only by construction)",
        verdict="no_edge",
        provenance="real-OOS",
        summary="No edge as a price-only model; the conditional alt-data "
        "extension never fired — its precondition (a promising 31b) was not "
        "met, so the simpler model stands.",
        evidence="validate_engine_oos · all horizons/commodities",
        rerun="uv run --directory apps/api python -m seeds.validate_engine_oos",
        gate_ref="docs/PHASE_31_PLAN.md §sequencing (31c closed)",
        updated="2026-07-25",
        doc_anchor="The conditional alt-data extension",
        doc_marker="No edge",
    ),
    LedgerRow(
        key="ensemble_gradient",
        claim="Ensemble confidence tiers predict accuracy",
        verdict="no_edge",
        provenance="real-OOS",
        summary="No reliable out-of-sample confidence gradient at any "
        "horizon; shipped reframed as down-weighting miscalibrated models, "
        "never as a calibrated confidence claim.",
        evidence="walk-forward ensemble-calibration harness (26c)",
        rerun=None,
        gate_ref="tests/test_ensemble_calibration.py (locked)",
        updated="2026-06-06",
        doc_anchor="confidence gradient** (26c)",
        doc_marker="No reliable OOS gradient",
    ),
    LedgerRow(
        key="carry",
        claim="Curve slope (carry) predicts forward direction",
        verdict="no_edge",
        provenance="real-OOS",
        summary="Time-series carry on NG+CL over ~5y: worse than drift at "
        "both horizons, adequately powered. Does not refute the "
        "cross-sectional literature — the curve archive accumulates toward "
        "that re-run.",
        evidence="validate_d2_carry · n_eff≈116 @1m (above the power floor)",
        rerun="uv run --directory apps/api python -m seeds.validate_d2_carry",
        gate_ref="docs/PHASE_D2_PLAN.md (gates + power rule pre-registered)",
        updated="2026-07-25",
        doc_anchor="Carry / term-structure",
        doc_marker="No signal on this design",
    ),
    LedgerRow(
        key="storage_event",
        claim="Storage-day surprises drive a tradeable reaction",
        verdict="insufficient",
        provenance="real-OOS",
        summary="The premise itself is absent: release-day correlation with "
        "our consensus-free surprise is a tight zero on 559 events. The "
        "market's expectation is analyst consensus, which is not public "
        "data — we do not fabricate it.",
        evidence="validate_d4_storage_event · n=559 events, 14y",
        rerun="uv run --directory apps/api python -m seeds.validate_d4_storage_event",
        gate_ref="docs/PHASE_D4_PLAN.md (gates + power rule pre-registered)",
        updated="2026-07-25",
        doc_anchor="Storage-day event edge",
        doc_marker="INSUFFICIENT-N",
    ),
    # ── Promising / parked ────────────────────────────────────────────────
    LedgerRow(
        key="vol_premium_timing",
        claim="Our vol forecast vs implied vol times the variance premium",
        verdict="promising",
        provenance="real-OOS",
        summary="Premium-timing passes on 2 of 3 asset pairs (crude, "
        "equities) with consistent direction; on equities our forecast beats "
        "VIX as a realized-vol predictor by >2 SE. Not crowned: gold fails "
        "and the EWMA robustness arm fails — a design review is scheduled, "
        "and any surface needs its own gate first.",
        evidence="validate_d1_vol_premium · ~11y weekly, n_eff≈131/pair",
        rerun="uv run --directory apps/api python -m seeds.validate_d1_vol_premium",
        gate_ref="docs/PHASE_D1_PLAN.md (gate + tie-breaker rule pre-registered)",
        updated="2026-07-25",
        doc_anchor="Vol-premium timing",
        doc_marker="⬆️ PROMISING",
    ),
    LedgerRow(
        key="raw_har_benched",
        claim="Raw-variance HAR estimator",
        verdict="benched",
        provenance="real-OOS",
        summary="Failed its gate against EWMA and blew up on real crude "
        "(R² −1.06). Code and tests kept; never wired.",
        evidence="estimator_skill · real CL @1m",
        rerun="uv run --directory apps/api python -m seeds.validate_estimator_30b",
        gate_ref="docs/MODEL_DILIGENCE.md §ledger (30b gate)",
        updated="2026-06-08",
        doc_anchor="raw-variance HAR",
        doc_marker="benched",
    ),
    # ── Collecting (no claim is possible yet — and none is made) ──────────
    LedgerRow(
        key="weather_archive",
        claim="Weather degree-day forecast features",
        verdict="collecting",
        provenance="collecting",
        summary="Forecasts can only be validated against an archive of what "
        "was forecast at the time. Daily vintages persist automatically; "
        "validation re-enters after ~180 real vintage days spanning a winter.",
        evidence="weather_forecast_vintages · immutable daily archive",
        rerun=None,
        gate_ref="docs/PHASE_D5_PLAN.md (re-entry trigger recorded)",
        updated="2026-07-25",
        doc_anchor="Weather degree-day features",
        doc_marker="collecting",
    ),
    LedgerRow(
        key="curve_archive",
        claim="Futures-curve history (for the carry re-run)",
        verdict="collecting",
        provenance="collecting",
        summary="Expired contract months vanish from free sources, so the "
        "historical curve is otherwise unreconstructible. Daily snapshots "
        "persist; the cross-sectional carry test re-enters at ~2 years of "
        "vintages.",
        evidence="futures_curve_vintages · immutable daily archive",
        rerun=None,
        gate_ref="docs/PHASE_D2_PLAN.md (re-entry trigger recorded)",
        updated="2026-07-25",
        doc_anchor="Futures-curve vintages",
        doc_marker="collecting",
    ),
    # ── Methodology (how the measuring stays honest) ──────────────────────
    LedgerRow(
        key="diagnostics",
        claim="Per-model diagnostics (bias, Brier decomposition, drift)",
        verdict="methodology",
        provenance="synthetic",
        summary="The measurement machinery, validated on seeded data where "
        "the ground truth is known by construction.",
        evidence="services/model_diagnostics.py",
        rerun=None,
        gate_ref="docs/MODEL_DILIGENCE.md §ledger (26a)",
        updated="2026-06-06",
        doc_anchor="Per-model diagnostics",
        doc_marker="synthetic",
    ),
    LedgerRow(
        key="context_integrity",
        claim="Backtest features are symbol-scoped and release-date gated",
        verdict="methodology",
        provenance="methodology",
        summary="A correctness fix locked as tests: positioning context is "
        "filtered per market and gated on publication dates, so backtests "
        "can never mix commodities or peek at unpublished data.",
        evidence="tests/db/test_context_scoping.py + look-ahead property tests",
        rerun=None,
        gate_ref="docs/PHASE_31_PLAN.md §31a.0",
        updated="2026-07-24",
        doc_anchor="Backtest alt-data context integrity",
        doc_marker="methodology",
    ),
    LedgerRow(
        key="surprise_proxy",
        claim="Storage surprise on real data is a labeled, consensus-free proxy",
        verdict="methodology",
        provenance="methodology",
        summary="EIA publishes no analyst consensus, so the storage surprise "
        "is this week's change vs the same-week 5-year norm — always labeled "
        "a proxy, never passed off as a survey.",
        evidence="services/storage_features.py · locked label tests",
        rerun=None,
        gate_ref="docs/PHASE_31_PLAN.md §31a.0",
        updated="2026-07-24",
        doc_anchor="seasonal-norm proxy on real data",
        doc_marker="methodology",
    ),
    LedgerRow(
        key="skill_vs_luck",
        claim="Desk skill-vs-luck verdicts refuse to crown noise",
        verdict="methodology",
        provenance="methodology",
        summary="A Wilson 95% interval against the coin-flip baseline: "
        "'skill' only when the lower bound clears chance. Blind seeded desks "
        "correctly read as luck — the demonstration that the tool cannot be "
        "flattered.",
        evidence="desk_calibration.py · honesty-locked e2e in CI",
        rerun=None,
        gate_ref="tests/db/test_desk_skill_verdict_e2e.py",
        updated="2026-06-10",
        doc_anchor="skill-vs-luck verdict",
        doc_marker="methodology",
    ),
    LedgerRow(
        key="cross_asset_configs",
        claim="Index (ES) and rates (ZN) engine configurations",
        verdict="unvalidated",
        provenance="real-in-sample",
        summary="Hand-set plausible scales proving the loop runs cross-asset "
        "— explicitly not a predictive claim for equities or rates. The "
        "range band self-calibrates per series; the directional configs "
        "carry no edge claim.",
        evidence="services/asset_config.py · golden byte-identity locks",
        rerun=None,
        gate_ref="docs/MODEL_DILIGENCE.md §ledger (B5)",
        updated="2026-06-28",
        doc_anchor="Cross-asset configs",
        doc_marker="unvalidated",
    ),
)


def ledger_rows() -> list[dict[str, Any]]:
    """Display-order rows for the API (internal drift-lock fields dropped)."""
    out = []
    for r in ROWS:
        d = asdict(r)
        d.pop("doc_anchor")
        d.pop("doc_marker")
        out.append(d)
    return out
