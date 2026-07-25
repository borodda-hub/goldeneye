# Goldeneye — Master Build Plan

### Single source of truth · stability-first · Claude Code handoff-ready

*Drafted 2026-06-08. This document consolidates and supersedes the three diverged roadmap docs — `BUILD_ROADMAP.md`, `ROADMAP.md`, and `CALIBRATION_ROADMAP.md` — into one dependency-ordered plan, aligned to the strategy realignment and grounded in the technical audit (commit `2c5daad`). It is written to be handed directly to Claude Code planning. `HANDOFF.md` remains the living session-state log; this is the durable plan it points to.*

---

## 1. How to use this document

- **This is the only roadmap.** When it and any other doc disagree, this wins. The three prior roadmaps are to be archived (see §6).
- **It defines *what* and *in what order*, plus the *definition of done* for each item.** It does **not** specify file-level changes — that is the job of the per-phase `docs/PHASE_*_PLAN.md` produced in a Claude Code `/plan` session (see §7).
- **The organizing principle is stability before expansion.** We stabilize the base (clean baseline, contract integrity, honest docs), then *activate* the already-built moat, then *validate* on real data. Nothing flashy is built on an unstable or dishonest base.

---

## 2. Stability doctrine (the non-negotiables)

These are the disciplines that keep the build from wobbling, regressing, or drifting. Every phase inherits all of them. They are the heart of the "most stable" requirement.

**S1 — One primary thread (WIP = 1).** Exactly one phase is the active primary thread at any time. It is fully built, gated, and **promoted to `master`** before the next primary thread starts. The only permitted parallelism is (a) non-code owner/GTM work and (b) a tightly-scoped opportunistic item that touches *disjoint* files (see §5). This single rule prevents the branch-pileup and integration debt that three overlapping arcs would otherwise cause.

**S2 — The full gate, every phase.** `pnpm health` (= `make health`) green end-to-end: `ruff → mypy --strict → pytest → web lint → typecheck → web test`. No phase is "done" until the whole gate passes.

**S3 — Look-ahead safety is an invariant, not a feature.** Any new or changed model or resolution path is look-ahead-safe by construction and **passes the existing cheating-model proof** (`tests/test_backtest_lookahead.py`) unchanged. Never relax the strict `ts < as_of` chokepoint or the runtime assertions.

**S4 — Honest-gate culture.** Every predictive/calibration claim ships with a pre-registered acceptance gate and a data-provenance label (`synthetic | real-OOS | real-in-sample`) per `MODEL_DILIGENCE.md`. If a model fails its gate, we **say so and bench it** (the existing `factor_learned` / raw-HAR precedent), never quietly ship it.

**S5 — Test-lock every validated claim.** When a claim is validated, lock it as a regression test so no future change silently re-breaks it (the `test_vol_range.py` / `test_ensemble_calibration.py` pattern). Validated-but-network-dependent checks live as re-runnable manual diagnostics with a CI-locked synthetic counterpart.

**S6 — Claims gate (trust integrity).** Nothing reaches a UI screen or the public site unless it (a) matches the code and (b) carries its honest framing (no certainty/advice language; in-sample vs OOS labeled). The forbidden-phrase layer enforces part of this; the rest is a review checklist. This is what keeps the narrative from ever outrunning the code again.

**S7 — Docs change in the same commit as code.** A schema change without a `SCHEMA.md` update is an incomplete commit (existing `CLAUDE.md` rule). Extend this: any change that alters a claim updates `MODEL_DILIGENCE.md` in the same commit.

**S8 — Two-lane promotion.** `feat/*` → `develop` → deliberate `master` promotion with the push guard and explicit owner sign-off. Promote increments as their gate passes; do not batch unrelated work into one promotion.

---

## 3. Current baseline (where we start)

- **In-flight WIP to resolve first:** Phase 30d is complete on `feat/phase-30d-views` but **not promoted**; `packages/contracts` has **stale, un-CI-enforced** types. A stable build cannot start with dangling WIP — Stage F resolves both.
- **The moat is built but dormant:** structured ex-ante capture (`007_decision_capture`), auto-resolution (`auto_resolution.py`), model + desk calibration scorecards (`model_calibration.py`, `desk_calibration.py`), Devil's Advocate (endpoints) — all shipped, none fully activated.
- **Accounts schema present:** `007_users` is merged via `009_merge_heads`; the remaining work is the app-level Clerk wiring (PR #7) and enforcing per-`user_id` scoping.
- **Real price backfill exists:** `price_backfill.py` persists real Yahoo OHLC to the `price_bars` hypertable; per-contract coverage to be confirmed.
- **The one validated edge is vol/range** (real-OOS, 6/6 commodities); **direction has no real edge** (confirmed real-OOS) and the system correctly declines to manufacture one.

---

## 4. The consolidated build sequence

Four stages, strictly dependency-ordered. Each item lists: **maps-to** (prior plan lineage), **status**, **depends-on**, **effort** (S/M/L), and **definition of done (DoD)** — the gate that closes it.

### Stage F — Foundation / stabilize the base *(do first; small, high-leverage)*

> Rationale: you cannot stably *add* to a base that has dangling WIP, silently-drifting contracts, and lying docs. Fix the floor before building on it.

- **F0 — Clean the baseline.** *maps-to:* Phase 30d promotion. *status:* PROMOTE. *depends-on:* —. *effort:* S.
  Live-verify 30d (default reads `har_log`, all four view states render), promote `feat/phase-30d-views` → `master`. **DoD:** `master == develop`, nothing un-promoted, gate green.
- **F1 — Contract integrity + CI lock.** *maps-to:* DD risk R8 / HANDOFF contracts debt. *status:* BUILD. *depends-on:* F0. *effort:* S–M.
  Regenerate `packages/contracts` from the live schema; add a hermetic CI step that dumps `openapi.json` and **diffs against the committed contracts, normalizing the date-dependent default** (`chart/bars` `from`) so the diff isn't noisy; fail CI on real drift. **DoD:** contracts match schema; CI fails on intentional drift; gate green.
- **F2 — Documentation reconciliation.** *maps-to:* this consolidation. *status:* BUILD (doc). *depends-on:* —. *effort:* S.
  Execute §6: establish this file as SOT, archive the three prior roadmaps with supersession headers, create `docs/README.md` index, and file drift-correction tasks for `ARCHITECTURE.md` + the website. **DoD:** docs index exists; no doc contradicts the code or this plan without a "superseded/stale" banner.

### Stage A — Integrity / trust *(harden what exists)*

- **A1 — Narrative↔code realignment.** *maps-to:* DD risk R1. *status:* BUILD (mostly non-code/GTM). *depends-on:* F0. *effort:* S–M.
  Site + in-app copy match the code: drop "Prophet," lead with the decision/calibration story over the directional hero, honest data labeling (real vs delayed/seeded). **DoD:** S6 claims gate passes on every public + in-app surface.
- **A2 — Honest derived confidence.** *maps-to:* CALIBRATION P4 / DD risk R4. *status:* BUILD. *depends-on:* F1. *effort:* S.
  Replace the hardcoded LLM-envelope `"medium"` with confidence derived from ensemble agreement + vol-band width (inputs already exist in `ensemble.py`). **DoD:** no hardcoded confidence on LLM outputs; values are explainable; gate green; tests added.
- **A3 — Validation page.** *maps-to:* new. *status:* BUILD (content). *depends-on:* —. *effort:* S.
  Externalize `MODEL_DILIGENCE.md` into a public "how we validate" page (honesty as marketing). **DoD:** page published; matches the provenance ledger.

### Stage B — Moat / activate the calibration platform *(the defensible core; mostly activation, not new build)*

- **B1 — Schedule auto-resolution.** *maps-to:* CALIBRATION P3 / DD risk R5. *status:* ACTIVATE. *depends-on:* F0; real price coverage confirmed. *effort:* S–M.
  Wire a scheduled worker to `resolve_open_decisions`; confirm/extend real `price_bars` coverage so resolutions run on real data, not seeded GBM. **DoD:** open decisions auto-resolve on a cadence against real prices; idempotent; gate green; a resolved-decision regression test locked.
- **B3 — Accounts GA + per-user scoping.** *maps-to:* Phase 28 (accounts) / ROADMAP #6 / DD risk R3. *status:* BUILD. *depends-on:* F0. *effort:* M.
  Finish Clerk (PR #7); scope every query by `user_id`; enforce isolation. (Schema/migrations already present via `007_users`/`009`.) **DoD:** multi-user isolation tested; anonymous demo still works; gate green.
- **B2 — Surface skill-vs-luck.** *maps-to:* CALIBRATION P5 + P7. *status:* ACTIVATE. *depends-on:* B1 (resolved data) + B3 (`user_id`). *effort:* M.
  Promote the Model Calibration Scorecard + Desk Calibration Score into a first-class view: per-analyst Brier, desk leaderboard, explicit skill-vs-luck with the significance guardrail. **DoD:** the view renders real per-analyst calibration with the n-guardrail; gate green.
- **B4 — Decision/audit ledger + observability.** *maps-to:* Phase 28 ledger + CALIBRATION L-front + ROADMAP #7. *status:* BUILD. *depends-on:* B3. *effort:* M.
  Immutable "at the moment of decision, here is what you knew" view (compliance story); add OpenTelemetry/metrics + safety-violation alerting now that multi-tenant. **DoD:** append-only ledger view; key spans/metrics exported; gate green.
- **B5 — Cross-asset portability.** *maps-to:* ROADMAP #9 + CALIBRATION architecture principles. *status:* ✅ **PROMOTED TO LIVE** (`master == 1a7e650`, PR #11; CI green both lanes). *depends-on:* platform stable single-asset (B1–B2). *effort:* M.
  Made deadband, regime bands, and the registry **per-asset-class config** (`services/asset_config.py`), not hardcodes; lit up **two** non-commodity classes — `index` (ES) + `rates` (ZN). **DoD met:** ES/ZN run the full loop with no commodity hardcode leaking — verified live (ZN decision auto-resolved against real prices → calibration; treasury-scale numbers); existing assets byte-identical (golden lock, commodity+metal); S3 proof green; honest scenario degradation for the new classes. Carve-outs labeled `unvalidated` (`MODEL_DILIGENCE.md`): index/rates configs are hand-set, and the paper-engine tick value is pinned to legacy 10000 for existing commodities (issue #10). `pnpm health` green (951 backend / 419 web).

### Stage C — Validation / proof *(real-data verdict + the structural gap)* — ✅ **COMPLETE 2026-07-25** (C3 shipped 31a.0→31a→31b, verdict recorded; C3b closed — condition unmet; C3-prod live, issue #13 closed. Detail: `PHASE_31_PLAN.md` status sections.)

- **C3 — Real feature-history ingestion.** *maps-to:* Phase 31 (`PHASE_31_PLAN.md` **v2**, revised 2026-07-24 after a code audit of the v1 draft) + ROADMAP #1 (real CFTC/NWS) / DD risk R2. *status:* BUILD — **scope decided: 31a.0 (correctness pre-fixes: symbol-scoped as-of context, consensus-free surprise proxy for `factor_composite`, petroleum release-date trap) → 31a (backfill: COT ×6 + NG storage, paginated range fetch, idempotent upserts) → 31b (pre-registered verdict via an alt-data arm of `validate_engine_oos.py`)**. *depends-on:* B1 ✅. *effort:* L (≈2.5–3 days).
  **DoD:** `factor_composite` moves out of `unvalidated` in `MODEL_DILIGENCE.md` — validated *or* honestly retired (S4); the symbol-scoping + proxy fixes are test-locked (S5).
- **C3b — Trained model / alt-data logreg (conditional).** *maps-to:* Phase 31c / CALIBRATION P8 / ROADMAP #5. *status:* BUILD (only if C3's 31b gate PASSES). *depends-on:* C3. *effort:* M–L.
  If 31b shows real alt-data signal, extend `logreg` (weather degree-day features rank ahead of COT — see D5); else keep the honest baseline and say so. **DoD:** S4 gate decided and recorded.
- **C3-prod — Live EIA flow + observed-derived caveat.** *maps-to:* Phase 31d / **issue #13** / HANDOFF caveat-fragility flag. *status:* BUILD. *depends-on:* C3 (shares adapters; separate promotion by design). *effort:* S.
  Scheduled prod refresh so `/v1/fundamentals` serves `source:"eia"` with a fresh `as_of`; `data_provenance_caveat()` storage clause becomes observed-derived so the caveat tracks reality in both states. **DoD:** issue #13 acceptance met + caveat test matrix covers real-storage config; #13 closed on promotion.

*(GTM/non-code, tracked but not Claude-Code phases: C1 design-partner pilots, C2 skill-vs-luck methodology artifact — these consume the outputs of Stage B/C.)*

### Stage D — Edge expansion *(added 2026-07-24; hunt edge where the platform has proven skill, not where it has proven none)*

> Rationale: Phases 26/30 + the real-OOS diligence established *where not to look* — price-only
> direction is dead (36/36 cells), and the one validated skill is second-moment (vol/range)
> forecasting. Stage D follows the skill and the commodity-risk-premia literature instead of
> re-mining price direction. **Every D item is a hypothesis with a pre-registered gate (S4),
> benched loudly on failure — none is a promised edge.** Shared prerequisite: the C3 ingestion
> spine (range fetch → upsert → point-in-time as-of) generalizes to every new data type below.

- **D1 — Implied-vs-realized vol probe.** *maps-to:* the Phase-30 vol edge, extended against a market price. *status:* ⚖️ **PROBED 2026-07-25 — PARTIAL, recorded, no build** (G2 premium-timing passed on USO/OVX only — monotone, +5.6 ± 3.8 vol-pts low−high — but failed GLD/GVZ and the EWMA robustness arm; per the pre-registered verdict: revisit with more IV pairs (^VIX/SPY) or +2y data, gate unchanged. Detail: `PHASE_D1_PLAN.md §verdict`). *depends-on:* nothing. *effort:* M (probe done).
  The calibrated vol forecast is currently judged only vs *realized* outcomes; the classic monetizable form is forecast-RV vs **implied** vol. Pilot CL+GC via free proxies (CBOE OVX/GVZ through the existing Yahoo path; ETF option chains as fallback). Probe script first (the Phase-30 `vol-predictability probe` pattern) — UI only if the gate passes. **Pre-registered gate:** walk-forward, does (forecast RV − IV) predict the subsequent realized variance premium beyond the "IV is unbiased" baseline, at ≥ ~1 SE on `n_eff`? **DoD:** verdict recorded in `MODEL_DILIGENCE.md`; if PASS, a research surface ("market prices X% vol; our calibrated engine says Y%") ships behind S6 framing.
- **D2 — Carry / term-structure feature.** *maps-to:* the best-documented commodity risk premium (Gorton–Rouwenhorst; Koijen et al. "Carry"). *status:* ❌ **PROBED 2026-07-25 — FAIL on the testable design** (time-series slope-sign, NG+CL, ~5y, adequately powered n_eff≈116: worse than drift on Brier, non-monotone terciles; boundaries + non-refutation of the cross-sectional literature recorded in `PHASE_D2_PLAN.md §verdict`). **D2a curve vintage archive SHIPPED** (migration 013, rides the 31d tick) — re-entry: ≥~2y of 6-symbol vintages → per-symbol re-run + cross-sectional rank test. *effort:* M (probe done; archive collecting).
- **D3 — Cross-sectional systematic desk.** *maps-to:* the B1/B2 desk machinery, reused. *status:* ⏸️ **DEFERRED to D2's re-entry trigger** (2026-07-25 — seeding a desk on a just-refuted signal would build on a refuted premise; cross-sectional history is what the D2a archive accumulates). *depends-on:* D2 re-entry + B2 ✅. *effort:* S–M.
  Ranking beats timing statistically: blind carry-ranked (and momentum-ranked) long-short **paper** desks seeded beside momentum/contrarian/random, resolved by the real engine against real prices, judged by the existing Wilson skill-vs-luck verdict. Zero new judging machinery; doubles as the product demo of the calibration moat crowning (or refusing to crown) a real academic factor. **DoD:** desks live on the leaderboard with honest verdicts; no new resolution path (S3 untouched).
- **D4 — Event-window selective abstention (storage-day).** *maps-to:* the queued selective-abstention quick-win + C3's surprise proxy. *status:* BUILD. *depends-on:* C3 (31a surprise proxy + real storage history). *effort:* M.
  Weekly features are stale except on release day; EIA storage Thursdays have a documented announcement effect in NG. Test the sharp question only: *conditional on a large surprise vs the 5-yr norm, is the same/next-day move predictable?* The system abstains 4 days a week and emits a view only in the event window, carrying its own conditional calibration readout. **Pre-registered gate:** conditional hit-rate clears the Wilson bar vs 0.50 on event days only (multiplicity-honest — one pre-declared window, not a scan). **DoD:** S4 verdict; if PASS, ships as an abstaining view, never an always-on signal.
- **D5 — Weather degree-day data collection (start the clock now).** *maps-to:* the one causally-forward NG demand driver; C3b's preferred feature. *status:* ACTIVATE (collection), BUILD later (validation). *depends-on:* nothing. *effort:* S (collection).
  HDD/CDD **forecasts** cannot be backtested without an archive of what was forecast *at the time* — so validation is impossible until history accumulates. Land a tiny scheduled fetch (NOAA/CPC degree-day outlooks, free; the NWS adapter pattern) persisting forecasts + vintages now; validate after ~2 seasons. **DoD (collection):** idempotent scheduled persist with vintage stamps; explicitly labeled `collecting — unvalidatable yet` in `MODEL_DILIGENCE.md` so the claim can't outrun the data.

---

## 5. Dependency graph & parallelism

```
F0 ─┬─ F1 ─── A2 ───────────────┐
    ├─ F2 (doc, parallel)       │
    ├─ A1 (non-code, parallel)  │
    ├─ A3 (content, parallel)   │
    └─ B3 ──┐                   │
   B1 ──────┼── B2 ── B4        │  (A2 independent; slot before/with B)
            │                   │
            └── B5 (after B1–B2 stable)
   B1 ── C3 ──┬── C3b (conditional on 31b PASS)
              ├── C3-prod (31d, separate promotion — issue #13)
              ├── D2 ── D3
              └── D4
   D1 (independent — extends the validated vol edge)
   D5 (independent — data collection only; validation waits on the archive)
```

**Critical path:** F0 → F1 → B3 → B1 → B2 → B4 → C3 (31a.0 → 31a → 31b) → C3-prod → D1 → D2 → D3.
**Stage D ordering:** D1 first after C3 (highest expected value, independent of 31b's verdict);
D2 → D3 next; D4 opportunistic once 31a lands; D5 collection starts anytime (S-effort, parallel-safe).
**Legitimately parallel (disjoint files, per S1):** F2, A1, A3 (docs/content/GTM) alongside any code phase; B5 may overlap C3 only if file-disjoint and WIP discipline holds.
**Opportunistic (pull in only when file-disjoint and slack exists):** Phase 29 charting differentiators (+ TradingView UDF), scenario-fidelity momentum shocks, 30c regime-conditional vol, selective abstention (only after C3).
**Deferred with re-entry triggers (not killed):** Phase 27 concierge copilot (re-enter after Stage B + a partner asks; build it as an explain-only agent over the proprietary substrate, never advisory); Databento/CME tick feed (a paying customer needs intraday); mobile responsive pass (partner demand); calibrated-consensus meta-signal (year-2, needs scale).

---

## 6. Documentation reconciliation plan (best practices)

The repo has three overlapping roadmaps plus stale design docs. Drifted docs are a stability hazard because `CLAUDE.md` instructs Claude Code to *read the file, not infer* — so a lying doc actively misdirects the build. Reconcile using single-source-of-truth + supersede-don't-delete:

**6.1 Establish the hierarchy.**
- **Master plan (this file)** = the single roadmap SOT. All future "what next" decisions reference it.
- **`HANDOFF.md`** = living session-state log (where we are *right now*); it *points to* this plan, never re-specifies it.
- **`MODEL_DILIGENCE.md`** = the claims/provenance SOT; unchanged, authoritative for what's validated.
- **Design SOTs** (`SCHEMA.md`, `API_CONTRACTS.md`, `AI_BEHAVIOR.md`) = authoritative for their domain; kept current via S7.

**6.2 Supersede, don't delete (preserve history + rationale).**
- Add a banner to the top of `BUILD_ROADMAP.md`, `ROADMAP.md`, `CALIBRATION_ROADMAP.md`:
  > `> ⚠️ SUPERSEDED 2026-06-08 by docs/MASTER_PLAN.md. Retained for history; do not plan from this file. Live items absorbed into the master plan's reconciliation table.`
- Move them to `docs/archive/` (or keep in place with the banner). Their phase-level *detail* (e.g., the Phase 26/30 closeouts) stays valuable as history and as the lineage the master plan's "maps-to" column references.

**6.3 Fix stale design docs (file as Stage F2 tasks, do in-commit going forward).**
- **`ARCHITECTURE.md`** — correct the two known-stale sections: it claims "No backtest engine" (one exists since Phase 10) and lists a model lineup that predates the Holt/logreg/vol-range work. Add a pointer to `MODEL_DILIGENCE.md` for current model truth.
- **Website** — treat as a doc-adjacent artifact under the S6 claims gate (this is Stage A1).
- Confirm `DATA_SOURCES.md` reflects that real adapters exist and EIA is live (it reads mock-first).

**6.4 Add `docs/README.md` (index).** A short table: each doc, its role (SOT / living-state / design / superseded / phase-plan), and last-reviewed date. Prevents the next reader from planning off a stale file. New `docs/PHASE_*_PLAN.md` files are listed here as they're created.

**6.5 Ongoing rule (already in CLAUDE.md, reinforce):** docs change in the same commit as the code (S7); a stale doc is a bug.

---

## 7. Claude Code handoff protocol

This plan is the input to planning mode. Convert it to execution as follows.

**7.1 One phase → one `/plan` session → one `docs/PHASE_*_PLAN.md`.** For each ACTIVATE/BUILD item, run a `/plan` session that reads this master plan's entry (the DoD is the acceptance criteria) plus the relevant design SOTs, and emits a committed plan doc *before* implementing — per the existing `CLAUDE.md` workflow ("plan before code; commit the plan into `docs/`").

**7.2 Per-phase plan template** (each `PHASE_*_PLAN.md` should contain):
1. **Objective + DoD** — copied from this plan's entry.
2. **Verified facts** — interfaces/files read this session that the plan depends on (the `DILIGENCE_AND_30C_PLAN.md` "[V]" pattern — verify, don't infer).
3. **Change set** — files touched, by stack lane (backend / web / schema), respecting "one concern per session."
4. **Tests** — new/changed tests, and which claims get **test-locked** (S5).
5. **Gates** — the S1–S8 items that apply, explicitly checked.
6. **Migration/contract impact** — Alembic migration? then `make migrate`; schema change? update `SCHEMA.md` same commit; response-model change? `pnpm contracts:gen:local` + the F1 CI check.
7. **Promotion** — branch name (`feat/phase-XX-*`), and the sign-off note for `develop → master`.

**7.3 Use the existing tooling/conventions** (per `CLAUDE.md`; local Claude Code config):
- `/health-check` (≡ `pnpm health` / `make health`) before declaring a phase done (S2).
- `/contract-check` whenever the FastAPI schema changes (now backed by the F1 CI lock).
- Sub-agents (`backend-builder`, `frontend-builder`, `schema-keeper`) for read-heavy lanes; respect the token-budget rules (reference docs by `§section`, one concern per session, diff-mode over new packages).
- Two-lane flow (S8); no `master` promotion without owner sign-off.

**7.4 Definition of Done for any phase** (the universal checklist):
`pnpm health` green · S3 look-ahead proof passes (if model/resolution touched) · S4 provenance recorded (if a claim changed) · S5 regression locks added · S6 claims gate (if a UI/site surface changed) · S7 docs updated in-commit · plan doc + code on `feat/*`, promoted to `develop`, queued for `master` sign-off.

---

## 8. The first three plan-mode sessions (start here)

Sequenced for stability and leverage; each is small and self-contained:

1. **F0 + F1 (one session) — clean baseline + contract lock.** Promote 30d; regenerate contracts; add the normalized OpenAPI dump-and-diff CI gate. *Why first:* a stable base with no dangling WIP and no silent FE/BE drift — the precondition for everything after, especially Stage B which adds endpoints/surfaces.
2. **A2 — honest derived confidence.** Retire the last hardcoded-confidence criticism; tiny, self-contained, touches the LLM-envelope + ensemble-agreement read. *Why second:* removes a known integrity gap before the calibration views (B2) surface confidence to users.
3. **B3 — accounts GA + per-user scoping.** The hidden prerequisite that unblocks B2's per-analyst skill-vs-luck and B4's ledger. *Why third:* it gates the moat's most valuable surface; schema is already present, so this is wiring + enforcement, not a from-scratch build.

(Run F2 — the doc reconciliation — as a parallel non-code task anytime; it's pure docs.)

---

## 9. Summary (paste-ready for Claude Code)

> **Goldeneye master build plan — single SOT, stability-first.** Supersede the three prior roadmaps (banner + `docs/archive/` + a new `docs/README.md` index); `HANDOFF.md` stays the living-state log pointing here; `MODEL_DILIGENCE.md` stays the claims SOT. Stability doctrine governs every phase: WIP=1 primary thread promoted before the next, full `pnpm health` gate, look-ahead-safety invariant + cheating-model proof, honest-gate (pre-registered acceptance + provenance, bench-and-say-so on failure), test-lock validated claims, a claims gate so no UI/site surface ever outruns the code, docs-in-commit, two-lane promotion. Build order is dependency-strict: **Stage F** (promote 30d → fix+CI-lock the contracts → reconcile docs) → **Stage A** (site↔code, honest derived confidence, validation page) → **Stage B, the moat** (schedule the built auto-resolution → finish accounts/per-user scoping → surface the per-analyst skill-vs-luck scorecards → immutable decision/audit ledger + observability → make the engine per-asset and add a second asset class) → **Stage C** (real COT/EIA feature-history ingestion = Phase 31, validating or honestly retiring the directional models → conditional trained model). The moat is already built — Stage B is mostly *activation*, not new code. Charting, the agentic copilot, tick feed, and mobile are parked with explicit re-entry triggers; quick-wins stay opportunistic under WIP discipline. Each ACTIVATE/BUILD item becomes one `/plan` session → one committed `docs/PHASE_*_PLAN.md` (template in §7.2) before code, gated by the universal DoD in §7.4. Start with: (1) F0+F1, (2) A2, (3) B3.

> **Addendum 2026-07-24:** Stages F/A/B are complete and promoted. Stage C is scoped via
> `PHASE_31_PLAN.md` **v2** (code-audit-corrected: 31a.0 pre-fixes → 31a backfill → 31b
> pre-registered verdict; 31c conditional; C3-prod/31d resolves issue #13 separately). A new
> **Stage D — edge expansion** follows the platform's proven skill (vol) and the commodity
> risk-premia literature: D1 implied-vs-realized vol, D2 carry/term-structure, D3 cross-sectional
> systematic desks, D4 storage-day selective abstention, D5 weather-forecast archival. Every D
> item is gate-first (S4) — a hypothesis to test honestly, never a promised edge.

*Lineage: consolidates `BUILD_ROADMAP.md`, `ROADMAP.md`, `CALIBRATION_ROADMAP.md`; aligned to the strategy realignment; grounded in the technical DD audit at commit `2c5daad`.*
