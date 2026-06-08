# Phase F Plan — Stage F0 (clean-baseline verify) + F1 (contract integrity + CI lock)

*Plan-only. Produced in a `/plan` session per `MASTER_PLAN.md §7.1`. Covers **F0 and F1 only**
(F2 doc reconciliation already shipped — `11d9748`/`db633c8` on `develop`). No code changed by
this document. Template follows `MASTER_PLAN.md §7.2`.*

**Source plan:** `MASTER_PLAN.md §4 (Stage F)` — F0, F1.
**Branch baseline (verified this session):** `master == origin/master == 2c5daad`;
`develop == origin/develop == db633c8`; `develop` is ahead of `master` by **3 doc-only commits**
(F2 + the session-end-rule doc). `git diff master develop -- apps/ ` is **empty** → all
application code is identical on both branches (verified).

---

## 0. Key finding up front (a deviation from the Master Plan's F1 premise)

`MASTER_PLAN.md §4/§6` says to normalize *"the date-dependent default (`chart/bars` `from`)"* so
the OpenAPI diff isn't noisy. **The code does not match that premise.** Verified at `2c5daad`:

- `chart/bars` `from` is a **fixed** literal — `from_: date = Query(default=date(2025, 5, 10), alias="from")`
  (`apps/api/routers/chart.py:47`). It renders as a *static* `"default":"2025-05-10"` and does **not**
  change day-to-day.
- The genuinely dynamic params use `default_factory=date.today` (`to` at `chart.py:48`/`patterns.py:62,84`/
  `signals.py:169`; `as_of` at `chart.py:146`). **With the installed FastAPI/Pydantic, `default_factory`
  emits *no* `default` key in the schema at all** — confirmed: in the committed
  `packages/contracts/openapi.json`, every `to`/`as_of` param has `"schema":{...,"title":"To"}` with
  **no** `"default"`. So they are not a diff-noise source either.
- The only date-shaped defaults present in the committed schema are all **fixed**: 3× `"2025-05-10"` and
  1× `"2026-01-01"`.

**Conclusion:** as the code stands today there is **no day-to-day date noise** in the generated schema.
The normalization step the Master Plan calls for is therefore a **defensive guard** (cheap insurance
against a future change that flips a param to a today-based default that *does* serialize), not a fix for
active noise. F1 will still implement it — robustly and documented — but the plan records that the named
"`chart/bars from`" is already stable.

**Why the guard exists at all (provenance):** the "date-dependent `chart/bars from`" framing was inherited
from an earlier HANDOFF/roadmap description that is now **stale** relative to the code — it assumed `from`
defaulted to today, which the code does not do (it's the fixed `2025-05-10` literal). We ship the guard
anyway because it's cheap and protects against the schema *becoming* date-dependent later, and we record
the stale-premise lineage here so the next reader knows the guard is intentional, not cargo-culted.
*(Surfacing this rather than silently building to a false premise — S6/S7.)*

A second verified gap that F1 must close to be meaningful: **CI never runs on the `develop` lane.**
`.github/workflows/ci.yml` triggers only on `push`/`pull_request` to `[main, master]`. Our flow is
`feat/* → develop → master`, so a contract check that only runs on master would never gate the lane where
contracts actually drift. F1 broadens the triggers (see §3).

---

## 1. Objective + DoD

### F0 — Clean the baseline *(verification/confirmation, NOT a new promotion)*
**Objective:** Confirm the already-live Phase 30d state on `master` is correct and complete; do **not**
re-promote (30d is live at `2c5daad`).
**DoD (from `MASTER_PLAN.md §4` F0, adapted to verify-only):**
- `master == develop` for **application code** (docs may differ) — **already true** (`git diff` empty).
- `GET /v1/forecast/range` defaults to `estimator=har_log` and `?estimator=ewma` is the opt-out.
- All four Signal Lab view states render: **Both** (default), **Range**, **Direction**, plus the
  EWMA·log-HAR estimator selector (visible only in range-bearing views).
- `pnpm health` green end-to-end.
- Outcome recorded in `HANDOFF.md` (F0 = confirmed live, no promotion needed).

### F1 — Contract integrity + CI lock
**Objective:** Regenerate `packages/contracts` from the live schema so it matches code, then add a
hermetic CI step that dumps `openapi.json`, normalizes date-shaped defaults, and **fails CI on real
drift** between the live schema and the committed contracts.
**DoD (from `MASTER_PLAN.md §4` F1):**
- `packages/contracts/openapi.json` + `packages/contracts/src/index.ts` match the live FastAPI schema at
  HEAD (regenerated; no diff on a clean run).
- A CI job dumps the schema, normalizes the date-dependent defaults, and **fails on intentional drift**
  (proven by a scratch edit during the build, then reverted).
- The check runs on the `develop` lane as well as `master`.
- `pnpm health` green.

---

## 2. Verified facts (read this session — `[V]` = confirmed in code, do not re-infer)

**Contracts tooling**
- `[V]` Root `package.json` scripts: `contracts:gen` = `curl -s http://localhost:8000/openapi.json | pnpm --filter @ngti/contracts exec openapi-typescript /dev/stdin -o src/index.ts`; `contracts:gen:local` = `pnpm --filter @ngti/contracts run gen`; `health` = the full gate.
- `[V]` `packages/contracts/package.json`: name `@ngti/contracts`; `scripts.gen` = `openapi-typescript ./openapi.json -o ./src/index.ts`; `scripts.typecheck` = `tsc --noEmit`; devDep `openapi-typescript: ^7`.
- `[V]` Committed artifacts: `packages/contracts/openapi.json` (~53 KB) and `packages/contracts/src/index.ts` (the generated types). `node_modules/` present in the package.
- `[V]` **Canonical 2-step regen** (matches `HANDOFF.md` gotcha; the only flow that refreshes *both* files): `curl -s http://localhost:8000/openapi.json -o packages/contracts/openapi.json` **then** `pnpm contracts:gen:local`. Note: the root `contracts:gen` script writes `-o src/index.ts` relative to CWD and does **not** update the committed `openapi.json`, so it is not the source of truth for regen.

**OpenAPI dump (hermetic, for CI)**
- `[V]` App object: `app = FastAPI(title="Goldeneye API", version="0.2.0", lifespan=lifespan)` at `apps/api/src/main.py:57`. Committed schema's `info` matches (`"title":"Goldeneye API","version":"0.2.0"`).
- `[V]` `app.openapi()` is **DB/Redis-free**: the only startup side-effect (`start_ticker`) is inside the `lifespan` context (`main.py:51-54`), which is *not* entered by `app.openapi()`; the DB engine is created lazily. → schema can be dumped without containers. *(Build step must still confirm the import is truly side-effect-free in the CI runner; runtime check, not a planning assumption.)*
- `[V]` `src.main:app` is the documented import path (used by the `dev` uvicorn command). Project-root bootstrap in `main.py:9-14` makes `apps.api.*` importable when run from `apps/api/`.

**CI**
- `[V]` Single workflow `.github/workflows/ci.yml`; 6 jobs: `lint-api` (ruff), `typecheck-api` (mypy --strict), `test-api` (pytest), `lint-web` (biome), `typecheck-web` (tsc --noEmit), `test-web` (vitest).
- `[V]` Triggers: `push`/`pull_request` to `[main, master]` **only** — `develop` is not covered.
- `[V]` Job idioms to reuse: Python jobs use `astral-sh/setup-uv@v5` + `uv sync --group dev` (working-directory `apps/api`); web jobs use `pnpm/action-setup@v4` + `actions/setup-node@v4` (node 20, pnpm cache) + `pnpm install --frozen-lockfile`.

**Date-default behavior** (see §0)
- `[V]` `chart.py:47` `from` = fixed `date(2025, 5, 10)`; `chart.py:48` & `:146`, `patterns.py:62,84`, `signals.py:169` use `default_factory=date.today`.
- `[V]` In committed `openapi.json`: `to`/`as_of` params carry **no** `default`; static date defaults are 3× `2025-05-10` + 1× `2026-01-01`.

**F0 surfaces**
- `[V]` `apps/api/routers/forecast.py:47-51` — `GET /range`, `estimator: str = Query(default="har_log")`; validates against `ESTIMATORS`, `?estimator=ewma` opt-out (module docstring `forecast.py:8-9`).
- `[V]` `apps/web/components/signals/SignalViewControls.tsx:8` — `export type SignalView = "both" | "range" | "direction";` (Both default; Direction hides the range *and* estimator selector — `:15,24,30,35`).
- `[V]` `apps/web/components/signals/ExpectedRange.tsx`, `SignalViewControls.tsx`, `app/(app)/signals/SignalsShell.tsx` carry the `har_log`/`ewma` wiring; component tests exist under `components/signals/__tests__/`.
- `[V]` `git diff master develop -- apps/` empty → har_log default + view states already on `master` (`2c5daad`).

---

## 3. Change set (by stack lane; respects "one concern per session")

> F0 touches **no files** (verification only). F1 is the build. F1 spans the **schema-artifact + CI**
> lane only (no `apps/api` logic, no `apps/web` logic) — keeps the concern tight.

### F0 — verification only
- No file changes. Run the live + gate checks in §1, record the outcome in `HANDOFF.md` (already names
  30d live; just affirm F0 confirmed). If any check fails, F1 is blocked and the failure becomes its own
  fix task (not in scope here).

### F1 — contract artifacts + CI lock
1. **Regenerated artifacts (data, not logic):**
   - `packages/contracts/openapi.json` — refreshed from the live schema at HEAD (expected: no change or a
     small, real delta if the committed copy drifted; the diligence audit flagged historical drift).
   - `packages/contracts/src/index.ts` — regenerated via `pnpm contracts:gen:local` from the refreshed JSON.
2. **New CI gate** — extend `.github/workflows/ci.yml` with a `contracts` job that:
   - sets up uv (mirroring `lint-api`), `uv sync --group dev` in `apps/api`;
   - **dumps** the live schema hermetically:
     `uv run python -c "import json; from src.main import app; print(json.dumps(app.openapi()))"`
     (working-directory `apps/api`) → `openapi.fresh.json`;
   - sets up node/pnpm (mirroring `typecheck-web`), `pnpm install --frozen-lockfile`;
   - **regenerates** types from the fresh dump (`openapi-typescript openapi.fresh.json -o index.fresh.ts`);
   - **normalizes** date-shaped `default` values in *both* the fresh and committed `openapi.json` before
     comparing (replace `"default":"<ISO-date>"` → `"default":"<DATE>"`), so any future today-based default
     can't make the diff flap. Document the one tradeoff: a deliberate change to a *fixed* date default is
     normalized away too — acceptable, since fixed-date changes are rare and visible in code review.
   - **diffs** committed-vs-fresh for both `openapi.json` (normalized) and `src/index.ts`; **fail** the job
     on any non-empty diff with a message pointing at the 2-step regen command.
3. **Broaden CI triggers** so the lock gates **both** the drift lane and the promotion gate:
   - `push.branches`: add `develop` (so the contracts job — and the whole suite — runs on every push to the
     integration lane where contracts actually drift). Keep `main`/`master`.
   - `pull_request.branches`: must include **both `develop` and `master`** — `develop` covers PRs landing on
     the drift lane, and **`master` covers the `develop → master` promotion PR** so the contract lock is a
     hard gate on promotion itself. (`master` is already listed; add `develop`.)
   - Net: the `contracts` job runs on pushes to `develop`/`master` and on PRs targeting `develop` *or*
     `master`. *(Verified gap: today CI triggers on `[main, master]` only, so it skips `develop` and never
     runs on the promotion PR if that PR targets `master` from `develop` — it does run, but only because
     `master` is the base; adding `develop` ensures the drift lane is covered too.)*
4. **Optional, recommended (small):** add a root `package.json` convenience script (e.g.
   `contracts:check`) that runs the dump→normalize→diff locally so a dev can reproduce the CI gate before
   pushing. Keep it shell-portable or a tiny Node script (the existing `contracts:gen` uses `/dev/stdin`,
   which is POSIX-only — the local check should not rely on that).

---

## 4. Tests

- **F0:** no new tests; the gate (`pnpm health`) + manual four-view live-verify *is* the check. Per the
  banked `h-full` lesson (`HANDOFF.md`), actually run the app and look at all four view states rather than
  trusting the component tests alone.
- **F1:**
  - The **CI `contracts` job is itself the regression lock** (S5) — it continuously asserts schema↔contracts
    parity.
  - **Prove it fails on drift** during the build: make a throwaway response-model/param change, confirm the
    job goes red, revert. Record this in the promotion note (don't commit the scratch change).
  - No unit tests are added to `apps/api`/`apps/web` (F1 is artifacts + CI; no app logic changes).
  - The existing `tests/contracts/` (OpenAPI round-trip) and web `typecheck` continue to run; the new job
    complements them by catching *committed-artifact* drift, which they do not.

---

## 5. Gates (S1–S8 from `MASTER_PLAN.md §2` — which apply)

- **S1 (WIP=1):** F0+F1 is the single active primary thread; F2 (docs) already landed in parallel as
  permitted. No other code thread runs concurrently.
- **S2 (full gate):** `pnpm health` green for F1 before "done."
- **S3 (look-ahead safety):** N/A — no model/resolution path touched. (Confirm: no change under
  `services/`.)
- **S4 (honest-gate / provenance):** N/A — no predictive/calibration claim changes.
- **S5 (test-lock):** the CI contracts job is the locked regression for schema↔contracts parity.
- **S6 (claims gate):** N/A — no UI/site copy changes (F0 only *reads* the existing honest UI).
- **S7 (docs-in-commit):** if regen reveals the committed schema had drifted, that's a contracts data fix;
  this plan doc + a `HANDOFF.md` update ship with the change. `API_CONTRACTS.md` is checked for staleness
  against any real schema delta and updated in the same commit if needed.
- **S8 (two-lane promotion):** `feat/phase-f-contracts` → `develop` → owner sign-off → `master`.

---

## 6. Migration / contract impact

- **Alembic migration?** No — no schema/DB change.
- **`SCHEMA.md` update?** No DB change → no update.
- **Response-model change?** No — F1 *captures* the current schema; it does not change any endpoint. If
  the regen surfaces a real committed-artifact drift, that delta is data-only (regenerated files), and
  `API_CONTRACTS.md` is reconciled in the same commit if the drift is user-visible (S7).
- **Contract regen:** the core of F1 — `curl … -o packages/contracts/openapi.json && pnpm contracts:gen:local`
  (or the new `contracts:check`/CI equivalent). This is exactly the F1 CI lock being established.

---

## 7. Promotion

- **Branch:** `feat/phase-f-contracts` off `develop`.
- **Commits (suggested split):**
  1. `chore(contracts): regenerate packages/contracts from live schema at HEAD` (artifacts only).
  2. `ci: add hermetic OpenAPI dump-and-diff contract gate + run CI on develop` (workflow + optional local script).
  3. `docs(phase-f): record F0 verification + F1 contract lock` (`HANDOFF.md`, this plan's status).
- **Sign-off note (for `develop → master`):**
  > Phase F complete. F0: 30d confirmed live at `2c5daad` (har_log default + four view states verified
  > live; `master==develop` code-identical) — no re-promotion. F1: contracts regenerated to match schema;
  > hermetic dump-and-diff CI gate added (date-default-normalized) and **proven to fail on intentional
  > drift**, now running on `develop` + `master`. `pnpm health` green. Note: the Master Plan's named
  > "`chart/bars from`" was already a fixed (non-dynamic) default — normalization shipped as a forward
  > guard, documented in §0.
- **After promotion:** update `HANDOFF.md` sync block; next critical-path item is **A2** (honest derived
  confidence) per `MASTER_PLAN.md §8`.
```
