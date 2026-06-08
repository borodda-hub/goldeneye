# Phase A2 Plan — Honest derived LLM-envelope confidence

*Plan-only. Produced in a `/plan` session per `MASTER_PLAN.md §7.1`. Covers **A2 only**. No code
changed by this document. Template follows `MASTER_PLAN.md §7.2`.*

**Source plan:** `MASTER_PLAN.md §4 (Stage A → A2)` — *"Replace the hardcoded LLM-envelope
`"medium"` with confidence derived from ensemble agreement + vol-band width (inputs already exist
in `ensemble.py`). DoD: no hardcoded confidence on LLM outputs; values are explainable; gate
green; tests added."* Maps to DD risk **R4** / `TECHNICAL_AUDIT.md §8`.

**Scope guard (from the owner, non-negotiable):** this touches **ONLY the LLM narrative-envelope
confidence** (`SafetyEnvelope.confidence` set in `llm_explainer.py`). It does **not** modify the
vol/range bands (`vol_range.py` / `forecast.py`) or any directional model's own `confidence`
(`services/models/*`, `ensemble.py`'s `ensemble_confidence`). Those are read-only inputs here.

---

## 0. Key finding up front (the one decision to sign off)

There are **7 hardcoded-confidence sites, all in `llm_explainer.py`** (matches the audit's "7 call
sites"). But the A2 derivation method — *ensemble agreement + band width* — is only **meaningful for
the forecast-bearing narratives**. Verified by tracing every caller:

| LLM function | site | caller | Has ensemble agreement + band width? |
|---|---|---|---|
| `explain_signal` | `llm_explainer.py:200` | `signals.py:145`, `explain.py:81` | **Yes** — `signal_dict["agreement"]` (`signals.py:134`); ensemble at `signals.py:111` |
| `summarize_market` | `llm_explainer.py:117` | `dashboard.py:108` | **Yes (router-side)** — ensemble at `dashboard.py:99`; `market_ctx` doesn't carry it yet (`dashboard.py:102-107`) |
| `generate_thesis` | `llm_explainer.py:150` | `dashboard.py:148` | **Yes (router-side)** — `thesis_ctx` already carries `confidence: ensemble.get("confidence")` (`dashboard.py:142`); ensemble at `dashboard.py:99` |
| `narrate_scenario` | `llm_explainer.py:229` (`"low"`) | `explain.py:96` | **No** — a hypothetical scenario, no ensemble forecast |
| `review_journal_entry` | `llm_explainer.py:253` | `journal.py:148`, `explain.py:117` | **No** — reviews a user journal entry (decision-quality), no market forecast |
| `critique_thesis` | `llm_explainer.py:284` | `thesis.py:175` | **No** — reviews a user thesis; only `conviction_pct` (the analyst's own) is available |
| `devils_advocate` | `llm_explainer.py:335` | `thesis.py:202` | **No** — adversarial probe of a user thesis; same as above |

**Scope decision (settled by the owner):**
- **A2 covers ONLY the three forecast-bearing narratives** — `explain_signal` (`:200`),
  `summarize_market` (`:117`), `generate_thesis` (`:150`). For these, replace the hardcoded `"medium"`
  with confidence honestly derived from ensemble agreement + band width (the inputs verified in
  `ensemble.py`). This is the canonical A2 deliverable and where R4 actually points.
- **The four non-forecast sites are left completely untouched in this phase** — `narrate_scenario`
  (`:229`), `review_journal_entry` (`:253`), `critique_thesis` (`:284`), `devils_advocate` (`:335`):
  **no derivation, no constant changes, no relabeling.** There is no ensemble forecast behind a
  hypothetical scenario or a thesis review, so an "ensemble-derived" confidence would be dishonest
  (S6). These functions already carry **meaningful hand-written caveats** — that qualitative text is
  the honest value they provide. Whether their coarse `confidence` *label* should change at all is a
  separate UX decision for a later phase, explicitly **out of scope for A2**.

Net: A2 is a tightly-scoped, value-only change to three call sites plus one pure helper.

---

## 1. Objective + DoD

**Objective:** Replace the hardcoded `SafetyEnvelope.confidence="medium"` on the **three
forecast-bearing LLM narratives** (`explain_signal`, `summarize_market`, `generate_thesis`) with a
value honestly derived from the already-computed ensemble agreement + band width. The four
non-forecast narratives are out of scope and left exactly as-is.

**DoD (from `MASTER_PLAN.md §4` A2, scoped to the 3 sites):**
- No hardcoded confidence on the three forecast-bearing LLM outputs — each is derived.
- Derived values are **explainable** (a pure helper with a clear agreement×band-width rule).
- The derivation uses **only decision-time-available data** (S3) — confirmed below.
- A **regression test locks the new mapping** (S5), including the "never upgrades confidence" property.
- `pnpm health` green; S3 cheating-model proof passes unchanged; S6 claims gate passes on the UI
  surfaces that render the three derived envelopes.

---

## 2. Verified facts (read this session — `[V]` = confirmed in code, do not re-infer)

**The hardcoded sites (all in `apps/api/services/llm_explainer.py`)**
- `[V]` `:117` `summarize_market` → `confidence="medium"`; `:150` `generate_thesis` → `"medium"`;
  `:200` `explain_signal` → `"medium"`; `:229` `narrate_scenario` → `"low"`; `:253`
  `review_journal_entry` → `"medium"`; `:284` `critique_thesis` → `"medium"`; `:335` `devils_advocate`
  → `"medium"`. Each is the `confidence=` arg to `wrap_with_uncertainty(...)`.
- `[V]` Non-narrative LLM functions (`extract_prediction`, `extract_event`) return structured JSON and
  **do not** set an envelope confidence — out of scope, nothing to change.

**The derivation inputs (already computed in `apps/api/services/ensemble.py`)**
- `[V]` `compute_ensemble(...)` returns (`ensemble.py:231-246`): `confidence` (agreement-derived
  tier), `agreement` = `{bullish, bearish, neutral, total, input_diversity}`, `range` =
  `{low_pct, high_pct}`, `vol_regime`, `confidence_rationale`.
- `[V]` `confidence` is derived from the **winning weighted fraction**: `>=0.70 → "high"`,
  `>=0.50 → "medium"`, else `"low"` (`ensemble.py:131-142`), with a regime tie-break that forces
  `"low"` in `elevated`/`crisis` when models tie (`ensemble.py:153-161`). So **agreement is already
  reflected** in `ensemble["confidence"]`; A2 adds **band width** as the second factor.
- `[V]` **Band width** = `range["high_pct"] - range["low_pct"]` (fractional; empty-result default is
  `±0.02` → width `0.04`, `ensemble.py:92`/`180-181`).
- `[V]` Honest-scope docstring (`ensemble.py:11-17`): ensemble confidence is **relative, not a
  realized-hit-rate** — so the envelope label must stay a coarse 3-bucket relative signal, not imply a
  calibrated probability. The A2 mapping must preserve that framing.

**What each caller already has on hand**
- `[V]` `signals.py:111` builds `ensemble`; `:130-137` `signal_dict` carries `agreement`, `confidence`,
  `vol_regime` — **but not** the ensemble top-level `range` (only per-model `models[].range` at
  `:122-125`). → to derive from band width, the ensemble `range` must be passed in (1-line plumbing).
- `[V]` `dashboard.py:99` builds `ensemble`; `market_ctx` (`:102-107`) lacks agreement/range;
  `thesis_ctx` (`:135-147`) carries `confidence` but not agreement/range. Ensemble is in scope at the
  call site for both.

**Semantics + UI**
- `[V]` `SafetyEnvelope.confidence: Literal["low","medium","high"]` (`safety.py:67`);
  `wrap_with_uncertainty(..., confidence: str, ...)` (`safety.py:90-114`) — the value is a single
  envelope field, not a schema enum tied to a request type.
- `[V]` It is **rendered in the UI**: `DirectionalBiasCard.tsx:74` / `AiThesisCard.tsx:112` via
  `SafetyEnvelopeNote`, and directly in `DevilsAdvocateDrawer.tsx:140` + `ThesisCritiqueDrawer.tsx:136`
  (`...safety.confidence`). → **S6 claims gate applies** (values change on real screens), but the
  change is honest reframing, not forbidden language.

**Tests + config**
- `[V]` LLM tests live under `apps/api/tests/llm/` (`test_explain_signal_corpus.py`,
  `test_narrate_scenario.py`, `test_review_journal_entry.py`); ensemble tests in
  `apps/api/tests/test_ensemble.py`.
- `[V]` `test_explain_signal_corpus.py:20-32` already parametrizes over `(direction, confidence,
  vol_regime, agreement_*)` fixtures and asserts no forbidden phrases — a natural home/pattern for the
  new assertions.
- `[V]` `settings.llm_mode` defaults to `"fake"` (`settings.py:33`) → deterministic canned responses,
  so envelope-confidence assertions are hermetic (no network, no Docker).
- `[V]` The cheating-model / look-ahead proofs (`tests/test_backtest_lookahead.py`) live in the
  backtest path and **do not import `llm_explainer`** — A2 leaves them untouched (S3).

---

## 3. Change set (by stack lane)

> Backend-only (`apps/api`). The web app already renders `safety.confidence`, so no `apps/web` change
> is required for the values to appear — but the S6 review must eyeball the rendered result.

1. **New pure helper in `ensemble.py`** (keeps derivation next to its inputs; no new module):
   `derive_envelope_confidence(*, ensemble_confidence: str, band_width: float | None, vol_regime:
   str | None = None) -> Literal["low","medium","high"]`.
   - Start from `ensemble_confidence` (already agreement-derived + regime-tie-aware).
   - **Down-modulate by band width only** (wider band ⇒ more uncertainty ⇒ lower confidence; never
     upgrade): named constants `_WIDE_BAND_PCT` and `_VERY_WIDE_BAND_PCT` (proposed defaults `0.10`
     and `0.18` fractional — the implementer sanity-checks these against real ensemble `range` values
     before locking; the test locks whatever is chosen). Rule: `band_width >= _VERY_WIDE_BAND_PCT →
     "low"`; else if `band_width >= _WIDE_BAND_PCT` and base is `"high"` → `"medium"`.
   - `band_width is None` ⇒ return the agreement tier unchanged (graceful when a caller lacks a range).
   - Pure, synchronous, no I/O — trivially unit-testable.
2. **`signals.py`** — derive once and pass it in: compute
   `env_conf = derive_envelope_confidence(ensemble_confidence=ensemble["confidence"],
   band_width=ensemble["range"]["high_pct"] - ensemble["range"]["low_pct"],
   vol_regime=ensemble.get("vol_regime"))` and pass `envelope_confidence=env_conf` to `explain_signal`.
3. **`dashboard.py`** — same derivation from the in-scope `ensemble`, passed to `summarize_market` and
   `generate_thesis`.
4. **`llm_explainer.py`** — replace the literal on the **three forecast-bearing functions only**
   (`explain_signal`, `summarize_market`, `generate_thesis`): add an `envelope_confidence: str | None =
   None` kwarg; use it in `wrap_with_uncertainty`. Default `None` falls back to a conservative `"low"`
   (honest default when a caller can't derive — e.g. the thin `explain.py:81` `explain_signal` caller
   that lacks a full ensemble). **No literal `"medium"` remains on these three.**
5. **Docs in-commit (S7):** note the change in `docs/AI_BEHAVIOR.md` (the envelope-confidence on the
   three forecast narratives is now derived, not fixed) and update `MODEL_DILIGENCE.md` if it references
   the "hardcoded medium" gap; `TECHNICAL_AUDIT.md` R4 is marked addressed in the HANDOFF, not edited
   (it's a point-in-time report).

**Explicitly NOT touched (out of A2 scope):** the four non-forecast LLM functions —
`narrate_scenario` (`:229`), `review_journal_entry` (`:253`), `critique_thesis` (`:284`),
`devils_advocate` (`:335`) — keep their existing literals and hand-written caveats verbatim. Also
untouched: `vol_range.py`, `forecast.py`, `services/models/*`, `ensemble.py`'s `ensemble_confidence`
logic, `safety.py` (the `Literal` type is unchanged).

---

## 4. Tests (S5 — lock the mapping)

- **Helper unit test (the lock)** — `apps/api/tests/test_ensemble.py` (or a new
  `test_envelope_confidence.py`): a parametrized table over `derive_envelope_confidence`:
  - high agreement + tight band → `"high"`; high agreement + very wide band → `"low"` (down-modulation
    fires); high agreement + moderately wide band → `"medium"`.
  - medium agreement (any band) → `"medium"` or `"low"` per width; low agreement → `"low"`.
  - `band_width=None` → returns the agreement tier unchanged.
  - boundary values exactly at `_WIDE_BAND_PCT` / `_VERY_WIDE_BAND_PCT`.
  - "never upgrades" property: output rank ≤ input `ensemble_confidence` rank for all inputs.
- **Function-level (fake LLM mode)** — assert the three forecast narratives surface the **derived**
  value, not a constant: feed `explain_signal` a high-agreement/tight-band signal → envelope `"high"`;
  a split/wide one → `"low"`. (Extends the existing `tests/llm/test_explain_signal_corpus.py` fixtures,
  which already vary agreement.)
- **Regression guard** — a test asserting **no remaining literal** `confidence="medium"`/`"high"` in
  the three forecast-narrative functions (grep-style or AST) so the gap can't reappear. The guard is
  scoped to those three; the four non-forecast functions keep their literals and are explicitly
  excluded.
- **Untouched sites stay untouched** — existing `tests/llm/test_narrate_scenario.py` and
  `test_review_journal_entry.py` must pass **unchanged** (no behavior change there).
- Existing corpus/forbidden-phrase tests must still pass unchanged (the text generation is untouched;
  only the envelope field on the three forecast narratives changes).

---

## 5. Gates (S1–S8 from `MASTER_PLAN.md §2` — which apply)

- **S1 (WIP=1):** A2 is the single active primary thread (Stage F done; A1 is non-code/GTM and
  file-disjoint).
- **S2 (full gate):** `pnpm health` green before "done."
- **S3 (look-ahead safety — VERIFIED applicable & satisfied):** the derivation consumes only the
  ensemble dict, which is computed at request time from `ForecastContext.closes` (latest closes up to
  now) — **present-time data only**. No backtest/resolution path is touched; `llm_explainer` is not
  imported by the look-ahead/cheating-model proof, which therefore passes **unchanged**. The new helper
  is a pure function of already-computed, decision-time values — it cannot introduce future leakage.
- **S4 (provenance):** the envelope confidence is **not** a predictive/calibration claim (it's a coarse
  relative label, per `ensemble.py:11-17`) — but A2 must keep that framing honest in copy (no implied
  hit-rate). Record the change in `MODEL_DILIGENCE.md`/HANDOFF.
- **S5 (test-lock):** the helper table test is the regression lock.
- **S6 (claims gate — applies to the 3 derived sites' surfaces):** the changed values render via the
  shared `SafetyEnvelopeNote` on the signal/market/thesis narratives — `DirectionalBiasCard.tsx:74`
  (signal explanation) and `AiThesisCard.tsx:112` (generate_thesis), plus the market-summary surface.
  Review the rendered output; ensure no certainty/advice implication and that "low/medium/high" reads as
  *relative confidence in the narrative*, not a forecast probability. The `DevilsAdvocateDrawer` /
  `ThesisCritiqueDrawer` surfaces render the **untouched** non-forecast envelopes — unchanged by A2, so
  no review needed there.
- **S7 (docs-in-commit):** update `AI_BEHAVIOR.md` (+ `MODEL_DILIGENCE.md` if it cites the gap) in the
  same commit.
- **S8 (two-lane promotion):** `feat/phase-a2-confidence` → `develop` → owner sign-off → `master`.

---

## 6. Migration / contract impact

- **Alembic migration?** No.
- **Response-model / OpenAPI change?** **No** — `SafetyEnvelope.confidence` stays
  `Literal["low","medium","high"]`; only the runtime *value* changes. So `packages/contracts` is
  unaffected and the **F1 `contracts` CI gate stays green** (schema identical). Worth stating
  explicitly so the contract job passing is expected, not a surprise.
- **`SCHEMA.md`?** No DB change.

---

## 7. Promotion

- **Branch:** `feat/phase-a2-confidence` off `develop`.
- **Commits (suggested split):**
  1. `feat(ensemble): add derive_envelope_confidence helper (agreement × band width) + tests`.
  2. `feat(llm): derive narrative-envelope confidence from ensemble; retire hardcoded "medium"`.
  3. `docs(a2): record honest derived confidence; update AI_BEHAVIOR + HANDOFF`.
- **Sign-off note (for `develop → master`):** A2 complete — the three forecast-narrative envelopes
  (`explain_signal`, `summarize_market`, `generate_thesis`) now derive confidence from ensemble
  agreement + band width (pure `derive_envelope_confidence` helper, test-locked incl. the "never
  upgrades" property). The four non-forecast LLM envelopes are deliberately untouched (out of scope).
  S3 proof unchanged; contracts CI green (value-only, no schema change); S6 reviewed on the three
  affected surfaces. `pnpm health` green.
- **After promotion:** update `HANDOFF.md`; next critical-path item is **B3 — accounts GA + per-user
  scoping** per `MASTER_PLAN.md §8`.
```
