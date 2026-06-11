# docs/PHASE_B2_PLAN.md — Stage B2: Surface skill-vs-luck (the significance test)

_Plan-mode output per `MASTER_PLAN.md §7.2`. **Plan only — no code until owner sign-off.**_
_Branch (when built): `feat/phase-b2-skill-vs-luck`. Backend + frontend promote together._

---

## 1. Objective + DoD

**Objective.** The Desk Calibration card already ships and is *labeled* "skill vs. luck" —
but it never **measures** it. It shows raw Brier + a raw hit-rate + an `n ≥ 10` gate, and
nothing tests whether a desk's directional hit-rate is distinguishable from a coin flip. B2
closes exactly that gap: add a **statistical skill verdict** — a Wilson 95% confidence
interval on the directional hit-rate against the 0.50 chance baseline — and surface it.
The tool must **refuse to crown skill that isn't there**: because there is no real OOS
directional edge (Phase 26, confirmed real-OOS), the momentum / contrarian / random desks
must all correctly read **Luck**. That refusal is the honest product value, and it gets
**test-locked**.

**This is NOT "build the view."** The view, endpoint, service, card, and `n`-gate all exist
(verified §2). B2 is a **focused statistical + framing increment** on top of them.

**Definition of Done** (from `MASTER_PLAN.md §4 / B2`, sharpened to this gap):
- The desk endpoint returns, per analyst, a **Wilson 95% CI** on directional hit-rate and a
  **verdict ∈ {`skill`, `luck`, `insufficient`}** alongside the existing Brier / hit-rate /
  calibration-gap (all retained).
- The card renders the verdict with honest framing (S6) — never readable as "your analysts
  are guessing."
- A **random / coin-flip desk → `luck`** regression is locked (S5) as the honesty guard.
- `pnpm health` green end-to-end (S2); contracts CI red→green across the response-model
  change (F1); docs updated in-commit (S7).
- Endpoint stays **desk-wide** (no `user_id` scope — per-user calibration lives on the main
  `/v1/calibration` page; confirmed §2.3).

---

## 2. Verified facts (read this session — verify, don't infer; `[V]` = confirmed in code)

### 2.1 Backend — the service and what it already computes
- `[V]` `apps/api/services/desk_calibration.py` — `compute_desk_calibration(session, *, min_resolved=10)`
  groups **all** resolved (`resolved_direction in ("hit","miss")`) journal rows by `user_id`,
  and per analyst computes: `n`, `brier` (Brier on stated conviction-as-probability),
  `hit_rate`, `mean_conviction`, `calibration_gap` (= mean_conv − hit_rate·100), `qualifies`
  (= `n >= min_resolved`). Returns `{"analysts": [asdict(AnalystScore)…], "min_resolved": int}`.
  Sorted: qualifying first, then lowest Brier. (`desk_calibration.py:43-100`)
- `[V]` `AnalystScore` is a `@dataclass(frozen=True)` (`desk_calibration.py:32-40`) — adding
  fields means adding here + the dataclass is `asdict`-serialized.
- `[V]` `MIN_RESOLVED_FOR_SCORE = 10` (`desk_calibration.py:29`) — the existing `n`-gate;
  reuse it for the `insufficient` verdict (no new constant).
- `[V]` **The hit/miss data needed for the Wilson test already exists** — `hit_rate` is `hits/n`,
  so `hits = round(hit_rate·n)` is recoverable, but the clean change is to carry `hits`
  through `compute_desk_calibration` (it already iterates `items` with `r == "hit"`;
  `desk_calibration.py:71`). No new query, no new data, **no migration**.

### 2.2 Backend — the endpoint (the contract gap)
- `[V]` `apps/api/routers/calibration.py:22-36` — `GET /v1/calibration/desk` returns a **bare
  `-> dict`** (no `response_model`). `grep response_model` in the router → **none**. So the
  OpenAPI schema for this path is an **opaque object**, and the frontend `DeskAnalyst` type
  (`api.ts:747`) is **hand-written and un-CI-enforced**. → Introducing a Pydantic
  `response_model` is what makes the F1 contracts regen *real* and retro-fixes the opaque
  contract. (This is the "response-model change → contracts regen" the owner flagged.)
- `[V]` The endpoint is **auth-required when accounts are configured** via
  `user: User | None = Depends(get_current_user)` (`calibration.py:25`), open in the
  single-tenant demo. The docstring says the *visibility model* is "deferred to B2"
  (`calibration.py:32-33`). **B2 resolves it: desk-wide leaderboard, auth-required-in-
  multitenant retained** (no per-row scoping). No code change to the auth dep; update the
  docstring + `API_CONTRACTS.md` to remove "deferred to B2."

### 2.3 The "keep it desk-wide" decision (confirmed against code)
- `[V]` `compute_desk_calibration` takes **no `user_id` filter** — it intentionally scans all
  rows and groups by `user_id` (`desk_calibration.py:50-59`). Per-user scoping lives on the
  main calibration path: `GET /v1/calibration` passes `user_id=user.id if user else None`
  (`calibration.py:82`) into `compute_calibration`. **B2 keeps the desk endpoint desk-wide —
  do not add `user_id` scope** (per owner). The leaderboard is the cross-analyst view by design.

### 2.4 Frontend — the card and its wiring
- `[V]` `apps/web/components/calibration/DeskCalibrationCard.tsx` — header already reads
  "Desk Calibration · skill vs. luck" (`:68`); table columns `# / Analyst / Calibration(Brier)
  / Hit / Conv / Bias / n`; footnote explains Brier-vs-hit. **No verdict column, no CI.**
- `[V]` `apps/web/lib/api.ts:747-760` — hand-written `DeskAnalyst` + `DeskCalibrationResponse`
  interfaces; `getDeskCalibration()` (`:762`). `useDeskCalibration()` in `lib/queries.ts:374`.
- `[V]` Tests exist: `apps/web/components/calibration/__tests__/DeskCalibrationCard.test.tsx`
  (extend), `apps/api/tests/test_desk_calibration.py` (extend — synthetic `Row` namedtuple +
  `AsyncMock` session pattern, `test_desk_calibration.py:9-26`).

### 2.5 The live "null" (honesty target) — and a seed doc-drift nit
- `[V]` `apps/api/seeds/demo_sample_desk.py` seeds three **blind-strategy desks** —
  `momentum` / `contrarian` / `random` — direction fixed by rule **before** the outcome, then
  scored by the real auto-resolution engine. `random` = deterministic coin-flip (the luck
  baseline), assigned `_RANDOM_UID` (`:55,:157`). These are the live desks the verdict will
  judge; all three should land on **Luck** (no real directional edge).
- `[V]` **Seed doc-drift (non-blocking, out of B2 scope):** the docstring (`:9`) and the
  print (`:164`) say "momentum = NULL pool," but the code assigns `_MOMENTUM_UID` (`:151`).
  Harmless to B2 (we don't depend on the live seed for the lock — see §4). Flag for a later
  one-line seed-comment fix; **not** part of this branch (keeps B2 file-disjoint and small).

### 2.6 No existing Wilson helper
- `[V]` `grep wilson|confidence interval|1.96` → only `vol_range.py` z-tables
  (`_Z = {…0.95: 1.9600}`), no proportion-CI helper. B2 adds a small pure helper.

---

## 3. The statistic (pre-registered — S4)

**Directional skill verdict** on each desk's resolved up/down calls:

- Inputs: `hits` (correct directional calls), `n` (resolved hit+miss). Chance baseline `p₀ = 0.50`
  (a binary up/down call). `p̂ = hits / n`. `z = 1.9600` (two-sided 95%).
- **Wilson score interval** (correct for proportions near 0/1 and small `n`, unlike normal-approx):
  ```
  denom  = 1 + z²/n
  center = (p̂ + z²/(2n)) / denom
  half   = (z / denom) · sqrt( p̂(1−p̂)/n + z²/(4n²) )
  wilson_low  = center − half
  wilson_high = center + half
  ```
- **Verdict (trichotomy):**
  - `insufficient` — if `n < MIN_RESOLVED_FOR_SCORE` (the existing `n`-gate; verdict mirrors
    `qualifies == False`). No CI claim below the gate.
  - `skill` — if `wilson_low > 0.50` (the 95% CI lower bound clears chance → distinguishable
    from a coin flip).
  - `luck` — otherwise (CI straddles or sits below 0.50 → **not** distinguishable from chance
    at 95%, given this sample). This is the branch that catches momentum/contrarian/random.

**Why this is honest, by construction:** the verdict can only say `skill` when the *lower*
bound of a 95% interval is above chance — a deliberately conservative, sample-size-aware bar.
A 7-of-10 streak (`p̂ = 0.70`, `wilson_low ≈ 0.40`) reads **luck**, not skill. The random desk
(`p̂ ≈ 0.50`) reads **luck** at any `n`. The system cannot manufacture a directional edge it
doesn't have — consistent with the Phase-26 real-OOS finding (`MODEL_DILIGENCE.md`).

**Separation of axes (kept explicit in the UI):** the **Wilson verdict** is about *directional
correctness vs chance*; the **Brier / calibration-gap** (retained, unchanged) is about *whether
stated conviction is reliable*. Two different questions; the card shows both and never conflates
them.

---

## 4. Change set (by lane — "one concern per session," but B2 is a vertical slice that
must promote backend+frontend together, so both lanes ship on one branch)

### 4.1 Backend (`apps/api`)
1. **`services/desk_calibration.py`**
   - Add a pure helper `wilson_interval(hits: int, n: int, z: float = 1.96) -> tuple[float, float]`
     (the §3 formula; handle `n == 0` → `(0.0, 1.0)`, never called below the gate anyway).
   - Add a pure helper `skill_verdict(hits, n, *, min_resolved) -> Literal["skill","luck","insufficient"]`.
   - Carry `hits` per analyst (already iterated; `:71`). Extend `AnalystScore` with:
     `wilson_low: float | None`, `wilson_high: float | None`, `verdict: str`. Round CI to 4dp.
     `verdict = "insufficient"` when `not qualifies`, else from `wilson_low` vs 0.50.
   - Keep all existing fields and the existing sort. (Optional, low-risk: within qualifying
     analysts, `skill` could rank above `luck` before the Brier tiebreak — **propose: leave the
     sort as-is** to keep the diff minimal and the regression surface small; revisit only if the
     owner wants skill-desks pinned to the top.)
2. **`routers/calibration.py`**
   - Define Pydantic v2 response models — `AnalystScoreOut` (all `AnalystScore` fields incl. the
     three new ones) and `DeskCalibrationOut` (`analysts: list[AnalystScoreOut]`,
     `min_resolved: int`, plus a constant `baseline: float = 0.50` for the UI to label the test).
   - Set `@router.get("/desk", response_model=DeskCalibrationOut)`. The service still returns a
     dict; FastAPI validates/coerces it. **This is the contract change that makes F1 bite.**
   - Update the docstring: remove "visibility model … deferred to B2"; state the resolved model
     (desk-wide leaderboard; auth-required when accounts configured; open in single-tenant demo).
   - **No change to the auth dependency. No `user_id` scope** (§2.3).

### 4.2 Frontend (`apps/web`)
3. **`lib/api.ts`** — after contracts regen, update `DeskAnalyst` (+ `wilson_low`, `wilson_high`,
   `verdict`) and `DeskCalibrationResponse` (+ `baseline`) to match the regenerated schema
   (the hand-written type stays the import surface; values mirror the generated contract).
4. **`components/calibration/DeskCalibrationCard.tsx`**
   - Add a **Verdict** column: a small badge — `Skill` (`text-up`/green), `Luck`
     (`text-ink-3`/neutral), `Insufficient` (`text-ink-4`/dim, only for sub-gate rows).
   - Render the CI on the Hit cell for qualifying rows, e.g. `52% [48–61%]` (hit-rate with the
     Wilson bounds), so the verdict is legible, not a black box.
   - Rewrite the header sub-label + footnote per S6 (§5).
5. **`lib/queries.ts`** — no change expected (same hook/key); verify the query still types-checks
   against the updated response.

### 4.3 Schema / migration
- **None.** No DB or schema change — reads existing resolved journal rows. (`SCHEMA.md` untouched.)

---

## 5. S6 claims-gate copy (exact framing — never "your analysts are guessing")

- **Card sub-label:** keep "Desk Calibration · skill vs. luck."
- **Verdict legend / footnote (proposed string):**
  > **Skill vs. luck** is a significance test, not a grade. We take each desk's directional
  > hit-rate and ask whether its **95% confidence interval clears a coin flip (50%)**. `Skill`
  > = the lower bound beats chance on this sample; `Luck` = not yet distinguishable from chance
  > (a hot streak isn't proof); `Insufficient` = fewer than {min_resolved} resolved calls. The
  > **random desk lands on `Luck` by design — that's the test working**, refusing to call noise
  > skill. Separately, **Calibration** (Brier on stated conviction) measures whether confidence
  > is reliable. Descriptive decision-quality diagnostics, not advice.
- **Tone rule:** `Luck` is framed as *"not statistically distinguishable from chance given the
  sample,"* explicitly **not** an accusation of guessing. The momentum/contrarian desks reading
  `Luck` is presented as the honest, expected result (no real OOS directional edge), not a defect.
- Disclaimer rule (`CLAUDE.md` / `AI_BEHAVIOR.md §disclaimer`) already satisfied by the
  calibration page chrome; no forbidden phrases introduced (no "will profit," "buy/sell," etc.).

---

## 6. Tests (new/changed; ★ = test-locked claim, S5)

### 6.1 Backend — `apps/api/tests/test_desk_calibration.py` (extend, same mock pattern)
- **★ `test_random_desk_reads_luck` (THE honesty lock).** A synthetic coin-flip desk —
  `hits = misses` (e.g. 50/50, n=100) → `verdict == "luck"`, `wilson_low < 0.50 < wilson_high`.
  This is the regression that guards "the tool refuses to crown noise."
- `test_strong_desk_reads_skill` — e.g. 70/30 (n=100): `wilson_low > 0.50` → `verdict == "skill"`.
- `test_hot_streak_below_gate_reads_insufficient` — 7/10 with `min_resolved=10` boundary handled,
  and a sub-gate case (e.g. n=6) → `verdict == "insufficient"`, no skill claim.
- `test_small_sample_does_not_crown` — 6/10 (`p̂=0.60`, n=10): CI straddles 0.50 → `luck`
  (sample-size discipline; a small edge isn't significant).
- `test_wilson_interval_known_values` — assert `wilson_interval(hits, n)` against hand-computed
  bounds for a fixed `(hits, n)` (pins the math; catches a refactor silently changing `z` or the
  formula).
- Confirm the existing four tests still pass (the new fields are additive; Brier/gap/sort unchanged).

### 6.2 Frontend — `components/calibration/__tests__/DeskCalibrationCard.test.tsx` (extend)
- Renders a `Skill` badge for a `verdict:"skill"` row, `Luck` for `"luck"`, `Insufficient` for a
  sub-gate row; the CI string renders on qualifying rows; the S6 footnote text is present.

### 6.3 Contracts — F1 CI (`contracts` job)
- After `pnpm contracts:gen:local` (response-model now typed), `packages/contracts` gains the
  `DeskCalibrationOut` shape. Run `pnpm contracts:check` → green. The job is **proven to bite**:
  the response-model change is exactly the kind of drift F1 guards (red before regen → green after).

### 6.4 No `tests/db` change
- B2 adds no DB/migration/router-scope behavior, so the gated `db-tests` job is unaffected (the
  Wilson lock is a fast unit test under `test-api`, not a testcontainer test).

---

## 7. Gates (S1–S8 — explicit applicability)

- **S1 (WIP=1):** B2 is the single active primary thread; promoted to `master` before B4 starts.
- **S2 (full gate):** `pnpm health` green end-to-end (ruff → mypy --strict → pytest → web lint →
  typecheck → web test).
- **S3 (look-ahead invariant):** **Not touched.** B2 adds **no model and no resolution path** —
  it's a pure statistic over already-resolved rows at read time. The cheating-model proof
  (`tests/test_backtest_lookahead.py`) is unaffected; state this explicitly in the commit.
- **S4 (honest-gate + provenance):** the verdict is a **pre-registered statistical claim**
  (§3) with a conservative acceptance bar. Add a `MODEL_DILIGENCE.md` row: *desk skill verdict =
  Wilson 95% CI vs 0.50; momentum/contrarian/random expected `luck`, consistent with the
  no-real-directional-edge finding.* Provenance label: methodology (not a predictive edge claim).
- **S5 (test-lock):** §6.1 `test_random_desk_reads_luck` locks the honesty guard permanently.
- **S6 (claims gate):** §5 copy reviewed; no surface reads as "your analysts are guessing"; no
  forbidden phrases; no certainty/advice language.
- **S7 (docs in-commit):** `API_CONTRACTS.md` (desk response shape + drop "deferred to B2"),
  `MODEL_DILIGENCE.md` (the S4 row), router docstring. `SCHEMA.md` untouched (no schema change).
- **S8 (two-lane):** `feat/phase-b2-skill-vs-luck` → `develop` → owner-signed `master` promotion.

---

## 8. Migration / contract impact

- **Migration:** none (no schema/DB change).
- **Contract:** **yes** — introducing `response_model=DeskCalibrationOut` types a
  previously-opaque endpoint. Regen with `pnpm contracts:gen:local` (dev server up), then
  `pnpm contracts:check`; the F1 `contracts` CI job gates it red→green. Update `API_CONTRACTS.md`
  in the same commit (S7).
- **Backend + frontend promote together** (the card depends on the new fields; per the banked
  "FE/BE that depend on each other promote to live together" lesson).

---

## 9. Promotion

- **Branch:** `feat/phase-b2-skill-vs-luck`.
- **Sequence:** build backend (service helper + models + endpoint typing) → regen contracts →
  build frontend (verdict column + copy) → `pnpm health` green → `db-tests` unaffected →
  push branch, open PR to `develop` (CI incl. `contracts` green) → merge to `develop` →
  **owner sign-off** → fast-forward `master`.
- **Sign-off note (for `develop → master`):** "B2 — Wilson 95% skill-vs-luck verdict on the desk
  leaderboard; random desk locked to `luck`; response-model typed (F1 red→green); desk-wide (no
  per-user scope); S3 untouched; docs in-commit. `pnpm health` green."
- **Post-promote:** update `HANDOFF.md` (B2 done; next per `MASTER_PLAN.md §4` = **B4**
  decision/audit ledger) and `project_phase_state.md`.

---

## 10. Out of scope (explicit — do not pull in)

- Per-user scoping of the desk endpoint (stays desk-wide; per-user is the main calibration page).
- The B3b leaderboard *who-sees-whom* visibility model beyond "auth-required-in-multitenant"
  (resolved as desk-wide; finer visibility is a later product call, not B2).
- Fixing the `demo_sample_desk.py` momentum-NULL doc-drift (§2.5) — a separate one-line nit.
- Issue #8 (de-hardcode the SampleDeskBanner figure) — independent B1 follow-up.
- Any change to Brier, calibration-gap, the `n`-gate value, or the ensemble.
```
