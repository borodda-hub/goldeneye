# Goldeneye — Calibration Platform Roadmap

*The build plan for the decision-intelligence pivot. Pairs with `docs/INNOVATION_BRIEF.md`
(the strategy + code-grounded audit). Written 2026-06-06.*

## Strategic intent

We are not building a commodity tool. We are building **the calibration layer for
discretionary capital** — the system of record for *what an analyst believed at decision
time and whether they were right for the right reasons.* Commodities (NG/CL/HO/RB/GC/SI)
are the **beachhead**, because that's where our real official-source data and credibility
already are and where incumbents don't play. The core engine — conviction snapshot →
look-ahead-safe resolution → reliability/calibration scoring → skill-vs-luck attribution —
is **asset-class-agnostic by design.** Every architectural decision assumes equities,
macro/rates, FX, and crypto are coming.

**Durable differentiator:** Essentia/Inalytics/TipRanks measure skill-vs-luck *post-hoc*
from executed trades or public recos. We capture **ex-ante conviction at the point of
research, in-terminal.** That advantage is asset-independent — it's the flank that lets us
expand into equities from a direction incumbents ignore.

## Architecture-for-portability principles (bake in from day one)

- **Pluggable asset abstraction:** `{instrument, price/fundamental feed, resolution rule}`.
  Adapters are already protocol-based (`adapters/base.py` + `registry.py`); the missing
  piece is making the **resolution rule** part of that abstraction (today there is no
  resolution engine at all).
- **Instrument-agnostic decision ledger:** `decision → conviction → evidence → resolution
  → score`, no commodity-specific assumptions. The journal/calibration schema is already
  agnostic (`calibration.py` buckets by conviction, not by symbol) — keep it that way.
- **Per-asset-class parameters, not hardcodes:** the regime classifier
  (`moving_average_directional.py::classify`, hardcoded commodity vol bands) and the
  scoring deadband (`signal_scoring.py`, hardcoded 0.3%) must become per-asset-class
  config, not constants.
- **De-commoditize the registry:** `PETROLEUM_SERIES`, metals→`NullEnergyAdapter`,
  per-symbol CFTC codes are commodity assumptions in `registry.py` to abstract over time.

## Grounded reality check (from the code audit)

- ✅ **Auto-resolution reuses the backtest.** The look-ahead-safe backtest already scores a
  directional call against realized moves (`signal_scoring.score_forecast`, 3-layer time
  cutoff). Auto-resolution = that engine pointed at journal decisions.
- ✅ **Derived confidence is half-built.** `ensemble.py` already computes vote
  agreement / winning fraction — real signal sitting behind the hardcoded "medium."
- ⚠️ **Keystone gap — claims are prose, not structured.** A decision today is free-text
  hypothesis + conviction number. You cannot auto-resolve prose. Phase 2 formalizes the
  claim; everything downstream depends on it.
- ⚠️ **Backfill is feasible now, daily-first.** Prod prices are seeded GBM; adapters are
  read-through (nothing persists to the Timescale hypertables); the worker is a
  placeholder. The existing Yahoo integration gives free historical **daily** OHLC —
  defer expensive intraday history.
- ⚠️ **Model Brier needs probabilities.** Models emit `direction + {low/med/high}`, not a
  probability. Per-model reliability/Brier requires a confidence→P(up) mapping (or models
  emitting probabilities). Analyst reliability already works (humans give a number).

## Decision: how claims are captured (Phase 2)

**LLM-extract + confirm.** Analyst writes the thesis as prose (research-first, unchanged);
an LLM proposes the structured `{instrument, direction, horizon, threshold}`, the analyst
confirms/edits in one click. Lowest friction, preserves the product feel, still yields a
clean machine-resolvable claim. The confirm step mitigates extraction error. Reuses the
existing LLM layer.

## Phased plan (dependency-ordered)

| Phase | What | Depends on | Effort |
|---|---|---|---|
| **0** | **Honest rename of the "XGBoost" heuristic** (it's a weighted-factor composite, not trained ML). Kills the worst diligence landmine in hours. | — | S |
| **1** | **Historical backfill** — extend the Yahoo integration to fetch daily OHLC history → persist to the `price_bars` hypertable; stand up a real worker/ingest path (retire seeded GBM). | — | M |
| **2** | **Structured ex-ante decision capture** — LLM-extract + confirm `{instrument, direction, horizon, threshold}` on each decision; store alongside the existing conviction snapshot. *The keystone.* | — | M |
| **3** | **Auto-resolution engine** — resolve open decisions from market data by reusing the backtest's look-ahead-safe scoring. Built generic (resolution rule as an interface), not commodity-specific. | 1 + 2 | M |
| **4** | **Derived confidence** — replace hardcoded "medium" with ensemble agreement (data exists) + per-regime historical hit-rate. | 1 | S–M |
| **5** | **Model Calibration Scorecard** — reliability diagram + Brier per model/ensemble, grouped by regime. *Lead demo.* (Needs confidence→probability mapping.) | 1, 4 | M |
| **6** | **Devil's Advocate adversarial thesis engine** — automated bull/bear + pre-mortem over the existing scenario/evidence substrate. Framed as a discipline layer that travels across asset classes. *Parallel track — can start at Phase 1; highest wow-per-effort.* | existing substrate | S–M |
| **7** | **Desk Calibration Score** — per-analyst reliability with significance guardrails; the compounding, asset-agnostic moat. Unblocked by the accounts/per-user identity already shipped (PR #7). | 2, 3, accounts ✅ | M |
| **8** | **Trained, look-ahead-safe model** — replaces the renamed heuristic with genuine ML on backfilled history. | 1 | M–L |
| **L** | Agentic research copilot → immutable Decision Ledger (compliance/post-mortem) → (year-2) calibrated-consensus meta-signal. | above | L |

**Order vs. the original ask:** inserted Phase 2 (structured capture) *before* auto-resolution
as the hidden prerequisite, and pulled Devil's Advocate into a parallel track for an early
demo win. Everything else holds.

## The arc

Prove the calibration loop on commodities — where our data is real and the field is empty —
then generalize the engine, one adapter at a time, into the calibration layer for all
discretionary decision-making. **Commodities is where we earn the right; discretionary
capital writ large is the market.**
