# Phase B1 Plan — Schedule auto-resolution (the ledger compounds automatically)

*Plan-only. Produced in a `/plan` session per `MASTER_PLAN.md §7.1`. Covers **B1 only**. No code
changed by this document. Template follows `MASTER_PLAN.md §7.2`. Maps to DD risk **R5** / CALIBRATION P3.*

**Source plan:** `MASTER_PLAN.md §4 (Stage B → B1)` — *"Wire a scheduled worker to
`resolve_open_decisions`; confirm/extend real `price_bars` coverage so resolutions run on real data,
not seeded GBM. DoD: open decisions auto-resolve on a cadence against real prices; idempotent; gate
green; a resolved-decision regression test locked."* Depends-on: F0 (done), B3 (done — per-user
scoping live). Effort: S–M. **Status: ACTIVATE** — the engine is built; B1 is the scheduler + tests.

**Headline:** the resolution *engine* already exists, is look-ahead-safe, and is idempotent by
construction. B1 is (a) the thin scheduling layer that runs it on a cadence, (b) the missing **real-DB
end-to-end + idempotency** regression locks (today's tests are all mocked), and (c) a **labeled
"sample desk" demonstration cohort** that the scheduler resolves into a populated, varied calibration —
so the full loop is *showable now*, with zero users (settled requirement, §11.1; honesty label is the
one hard line, §8 S6). The four questions the owner flagged are answered in §3–§6 against verified code.

---

## 0. What already exists (verified — `[V]` = confirmed in code this session)

- `[V]` **`services/auto_resolution.py::resolve_open_decisions(session, *, now=None)`** resolves every
  open structured decision whose horizon has elapsed: measures `realized/anchor - 1` and scores it with
  **`signal_scoring.score_forecast`** (the *same* function the backtest uses), mapping outcome →
  `resolved_direction` (`_OUTCOME_MAP`, lines 31-38). Writes `resolved_direction`, `resolved_at`
  (tz-aware), `auto_resolved=True`; returns a `ResolveResult` (resolved / still_pending / no_price /
  by_outcome). Caller commits.
- `[V]` **Query is system-wide and idempotent** (`:90-99`): selects rows with `predicted_direction IS
  NOT NULL AND resolved_direction IS NULL AND anchor_price IS NOT NULL AND horizon_days IS NOT NULL` —
  **no `user_id` filter**, and **only `resolved_direction IS NULL` rows** (a manual/auto mark is never
  re-touched).
- `[V]` **`_realized_close`** (`:57-77`) reads the **first real 1d `price_bars` close on/after the
  target date** for the instrument's front-month contract — real prices, look-ahead-safe (target is in
  the past for any elapsed-horizon decision).
- `[V]` **Manual trigger exists:** `POST /v1/journal/auto-resolve` (`routers/journal.py:84-96`) calls
  `resolve_open_decisions` + `session.commit()`. (This is the J6 row B3 deliberately left system-wide.)
- `[V]` **No scheduler exists.** The `worker` service in `infra/docker-compose.yml:62-66` is a
  **placeholder** (`command: ["echo", "worker placeholder — Phase 02 wires real tasks"]`). No
  APScheduler/cron in the app.
- `[V]` **The background-task pattern is `start_ticker`** (`realtime/ticker.py:93-113`): launched from
  the FastAPI **lifespan** (`src/main.py:51-54`), it `asyncio.create_task()`s `while True: await
  asyncio.sleep(...)` loops. Out-of-request DB work uses **`db.session.get_session_factory()`**.
- `[V]` **Real price coverage EXISTS:** `price_bars` (1d) is **100% `source="yahoo_delayed"`** (real) —
  **0 mock/GBM rows**; **12,064 bars**, ~252/contract (≈1 trading year), spanning **2025-06-06 →
  2026-06-05**, across **NG / CL / RB / GC / HO** front+back contracts. So resolutions run on real data
  for the showcase commodities.
- `[V]` **But the showcase has ~0 open structured decisions right now:** of ~96 journal rows, only **1**
  is machine-resolvable (predicted_direction+anchor+horizon set) and it is **already resolved**. The
  rest are prose-only (no `predicted_direction`). → with no users, an empty calibration view would hide
  the whole value prop, so **B1 seeds a labeled "sample desk" cohort** of open decisions that the
  scheduler resolves into a populated, varied calibration (settled requirement — §11.1); the engine's
  regression lock uses a *separate* controlled decision (§3).
- `[V]` **Existing tests are mocked** (`tests/test_auto_resolution.py`): in-memory rows + patched
  `_realized_close`; they pin the scoring→resolution mapping and pending/no-price guards. **No
  idempotency test, no real-DB end-to-end test.** B1 adds both, in the gated `db-tests` suite.

---

## 1. Objective + DoD

**Objective:** Run the existing `resolve_open_decisions` on a cadence so the calibration ledger
compounds without a manual endpoint call — and lock its idempotency + real-data correctness as
regressions.

**DoD (from `MASTER_PLAN.md §4` B1):**
- Open structured decisions whose horizon has elapsed **auto-resolve on a cadence** against real
  `price_bars`.
- **Idempotent** — re-running never double-resolves or overwrites (only `resolved_direction IS NULL`);
  proven by a locked test (§4).
- **Look-ahead-safe** (S3) — unchanged `score_forecast`; the cheating-model proof still passes.
- A **resolved-decision regression test** is locked **in the gated `db-tests` suite** (real DB).
- **A labeled demonstration cohort exists and resolves into a populated, varied calibration**
  (hits *and* misses, a real-looking reliability diagram + skill-vs-luck readout) — and is
  **clearly labeled "sample desk / demonstration data," never presented as a real analyst track
  record** (the S6 honesty line; see §11). With zero users, this is the showable value, so it ships
  in B1.
- `pnpm health` green; the scheduler is **off-by-default-safe** for tests/CI and the single-process demo.

---

## 2. The scoping/identity question — a privileged system job (Q1)

`resolve_open_decisions` runs **outside any user request** (no `get_optional_user`, no `scope`) and
queries **all** open decisions with **no `user_id` filter**. This does **not** violate B3's per-user
isolation, and here is exactly why:

- **B3 isolation governs *user-facing* reads/writes** — what a signed-in analyst can see/modify over
  HTTP. The auto-resolver is a **privileged background job**, the same category as the existing
  `POST /v1/journal/auto-resolve` endpoint that B3 deliberately left system-wide (J6 in `PHASE_B3_PLAN
  §4.1`).
- **It never crosses users.** For each decision it reads **only that row's own** `anchor_price`,
  `horizon_days`, `predicted_direction`, `instrument_id`, and writes **only that row's own**
  `resolved_direction`/`resolved_at`/`auto_resolved`. It performs **no join across users** and surfaces
  **no user's data to another** — it stamps each decision's outcome in place. The row keeps its
  `user_id`.
- **The per-user views stay isolated.** A signed-in analyst's calibration still reads only their own
  resolved rows (`compute_calibration(..., user_id=scope)`, B3a) — so the worker resolving *everyone's*
  decisions is invisible across tenants; each user simply sees their own ledger fill in.
- **Safe-by-construction, made explicit in B1:** the scheduler must run with a **system session**
  (`get_session_factory()`), **never** a request-scoped `get_db`, and must **not** accept or apply a
  `user_id` — document it as the one intentional system-wide writer, so a future refactor doesn't
  "helpfully" add a scope filter (which would silently stop resolving most users' decisions).

---

## 3. Idempotency (Q2) + the lock test

**Why it's idempotent today:** the WHERE clause includes `resolved_direction IS NULL`, so any row
already resolved (manually *or* by a prior auto run) is **not selected** on the next pass. A re-run
therefore touches only still-open rows; a second immediate run resolves **0**. There is no upsert and
no overwrite path.

**The locked test (new, in `db-tests`):**
1. Seed an instrument + a front-month contract + one real `price_bars` close on/after the target date,
   and one **open** structured decision (`predicted_direction`, `anchor_price`, past `created_at +
   horizon_days`, `resolved_direction IS NULL`).
2. Run `resolve_open_decisions` (with `now` past the horizon) → assert `resolved == 1`, the row's
   `resolved_direction` is the expected hit/miss/neutral, `auto_resolved is True`, `resolved_at` set.
3. **Run it again** → assert `resolved == 0` and the row's `resolved_direction` / `resolved_at` are
   **unchanged** (capture before/after). This is the idempotency lock.
4. **Manual-mark guard:** seed a second decision with `resolved_direction='hit'` set manually; run the
   resolver; assert it is **untouched** (`auto_resolved` stays False, value unchanged).

Lock as a parametrized real-DB test so the "only-NULL, never-overwrite" invariant can't silently break.

---

## 4. Look-ahead safety + real-price coverage (Q3)

- **Look-ahead-safe (S3):** the resolver scores with the **unchanged `signal_scoring.score_forecast`**
  — the exact function the backtest uses — and only resolves decisions whose **horizon has already
  elapsed** (`target <= now`), reading the **first real close on/after `target`** (a past date). No
  future data enters. B1 changes **no model/resolution logic**, so the cheating-model proof
  (`tests/test_backtest_lookahead.py`) is untouched and must still pass.
- **Real coverage confirmed (Q3):** `price_bars` is 100% real (`yahoo_delayed`), ~1 trading year to
  **2026-06-05**, for NG/CL/RB/GC/HO — so elapsed-horizon decisions on the showcase commodities resolve
  on real prices. **Two honest edges to document, not hide:**
  - A decision whose **target date is after the last real bar (2026-06-05)** → `_realized_close`
    returns `None` → counted **`no_price`**, left open (re-resolves once coverage catches up). With dev
    "now" ≈ 2026-06-09 this is a small window; in production it's whatever the backfill freshness is.
  - **Backfill freshness is out of B1 scope** (it's `price_backfill.py`, run on demand). B1 should
    *confirm* coverage (done) and may **optionally** schedule a periodic backfill alongside resolution
    so fresh closes land before resolution runs — flagged as an opportunistic add, not required by DoD.

---

## 5. The scheduler mechanism + CI testability (Q4)

**Mechanism — recommended: an in-process, lifespan-launched, env-gated async loop** (mirrors
`start_ticker`), because it's the lowest-friction activation for the single-process demo and reuses the
proven pattern:
- New `services/resolution_scheduler.py` with:
  - `async def resolve_tick() -> ResolveResult` — acquires a **system session** via
    `get_session_factory()`, calls `resolve_open_decisions(session)`, **commits**, returns the result.
    *(This is the unit the tests drive — see below.)*
  - `async def run_scheduler()` — `while True: await resolve_tick(); await asyncio.sleep(interval)`
    (run once on boot, then every `interval`), wrapped in try/except so a transient error logs and the
    loop survives. Launched from the lifespan via `asyncio.create_task` **only when enabled**.
- **Settings (env-gated, off where it shouldn't run):** `auto_resolve_enabled: bool = False` and
  `auto_resolve_interval_hours: float = 24` in `src/settings.py`. Default **off** so tests/CI and any
  non-primary process don't spawn a loop; enabled in the deployed env. (Daily cadence matches the data:
  prices are daily; nothing resolves faster than a new daily close.)
- Wire `src/main.py` lifespan: `if settings.auto_resolve_enabled: asyncio.create_task(run_scheduler())`
  — right beside `start_ticker()`.

**Multi-replica caveat (documented, not solved in B1):** if the API runs N replicas each starting the
loop, they'd run N concurrent resolution passes. **Idempotency makes that correctness-safe** (no
double-resolve), just redundant. The clean scale answer — a **Postgres advisory lock** around
`resolve_tick`, or moving the loop into the dedicated `worker` service (replacing the compose
placeholder) so exactly one process schedules — is **flagged as the scale hardening**, deferred. The
demo runs a single API process, so the in-process loop is safe today.

**CI testability (Q4):** the **timing loop is thin, time-based glue** (like `start_ticker`, which has
no unit test) — B1 does **not** unit-test the `while True/sleep`. Instead:
- **`resolve_tick()` is fully testable** and is tested in the gated `db-tests` suite (real session →
  resolve → commit → re-query), covering correctness + idempotency (§3) on **real prices**.
- The endpoint path (`POST /v1/journal/auto-resolve`) keeps its existing mocked router test.
- Optionally, a **single-iteration harness** for `run_scheduler` (monkeypatch `asyncio.sleep` to raise
  `CancelledError` after the first tick) can assert "boot → one resolve → sleep scheduled" without a
  real wait — included if cheap, but the load-bearing coverage is `resolve_tick` in `db-tests`.

---

## 6. Change set (by stack lane)

**Backend — scheduler (`apps/api`):**
- `services/resolution_scheduler.py` (new) — `resolve_tick()` + `run_scheduler()` per §5.
- `src/settings.py` — `auto_resolve_enabled` (default `False`) + `auto_resolve_interval_hours`
  (default `24`).
- `src/main.py` — lifespan launches `run_scheduler()` when enabled (beside `start_ticker`).
- *(No change to `auto_resolution.py` itself — it's already correct; B1 only schedules it.)*
- *(Optional, §4) periodic price backfill tick — opportunistic, not in the DoD.)*

**Backend — demonstration cohort (`seeds/`, REQUIRED — see §11):**
- `seeds/demo_sample_desk.py` (new, modelled on the existing `seeds/demo_desk_analysts.py`) — seed a
  believable set of **open** structured decisions into the **anonymous/sample (`user_id IS NULL`)
  pool**: varied instruments (NG/CL/RB/GC/HO — all real-price-covered), varied conviction, and
  **already-elapsed (back-dated)** horizons — `created_at` set so `created_at + horizon_days < now` and
  the target is inside the real price window (≤ 2026-06-05) — with `anchor_price` taken from the **real
  historical close** at each decision's (past) `created_at`. Because horizons are pre-elapsed and prices
  are real, the **first scheduler tick resolves the whole cohort immediately into genuine hits/misses**
  (no day-long wait) — the *outcomes are real* (computed by the engine from real prices), only the
  *decisions* are sample. Calibrate the conviction/threshold mix so the resolved set yields a
  varied reliability diagram (some over-/under-confident buckets) and a non-trivial skill-vs-luck
  readout. Wire into the `seeds/demo` entrypoint behind an explicit flag.

**Frontend — the honesty label (REQUIRED, S6):**
- A clear **"Sample desk — demonstration data, not a real track record"** label on the calibration +
  journal showcase surfaces whenever the **anonymous/sample pool** is shown (i.e. signed-out / the
  demo). Uses the existing design tokens; no new component pattern needed (a banner/badge). A signed-in
  user sees *their own* (empty-until-used) ledger, never the sample data — so the label scopes to the
  demo view. This is the non-negotiable line in §11.

**Tests:**
- `tests/db/test_auto_resolution_e2e.py` (new, **gated db-tests**) — real-DB resolution + the
  idempotency/manual-mark locks (§3), on a **small controlled seed** (NOT the showcase cohort — the
  engine proof stays independent of demo data).
- Keep the existing mocked `tests/test_auto_resolution.py`.
- A seed smoke test (the sample-desk seed loads + resolves to a non-empty, varied calibration) may live
  in `db-tests`; the label is covered by a web component test.

**Docs (S7):** `ARCHITECTURE.md` (scheduler/worker tier now real, env-gated) + `MOCK_DATA_SPEC.md` (the
sample-desk cohort + its labeling rule) + `AI_BEHAVIOR.md` (sample-data labeling as a governed string) +
`HANDOFF.md`; update `infra/docker-compose.yml` worker comment if the worker-service path is chosen.

**Deploy (ops, noted not built):** enable `AUTO_RESOLVE_ENABLED=true` on the single deployed API
process (Railway). If/when multi-replica, switch to the advisory-lock or worker-service path.

---

## 7. Tests (S5 — what gets locked)

- **`db-tests` (gated, real DB) — the B1 acceptance lock:** seed instrument+contract+price+open
  decision → `resolve_tick`/`resolve_open_decisions` resolves it on real prices; **second run resolves
  0 and mutates nothing** (idempotency); a manually-resolved row is never overwritten. This runs in the
  CI `db-tests` job (B3a.1), so a regression turns CI red — same standard as the landmine + HTTP
  isolation locks. *(Prove-it-bites optional but available: break the `resolved_direction IS NULL`
  guard → the idempotency test goes red.)*
- **Existing mocked tests stay green** (scoring map, pending/no-price guards, endpoint).
- **S3:** cheating-model / look-ahead proofs unchanged and green.

---

## 8. Gates (S1–S8 — which apply)

- **S1 (WIP=1):** B1 is the single primary thread. (B2 depends on B1's resolved data + B3's `user_id` —
  sequence B1 → B2.)
- **S2:** full `pnpm health` green.
- **S3 (look-ahead — applies):** N/A to *new* logic (the resolver is unchanged); the proof must still
  pass. The scheduler only *invokes* the existing safe path.
- **S4 (provenance):** no predictive claim changes; the resolver's outcomes are mechanical scoring, not
  a model claim.
- **S5 (test-lock):** the `db-tests` resolution + idempotency suite.
- **S6 (claims gate — APPLIES, load-bearing):** the demonstration cohort is shown in the UI, so the
  **"sample desk / demonstration data, not a real track record"** label is a hard gate item — the
  calibration/journal showcase must never present sample decisions as a genuine analyst history. The
  *outcomes* are real (engine-scored from real prices), the *decisions* are sample; the copy must say
  exactly that. This is the credibility line; review it on every surface that renders the sample pool.
- **S7 (docs-in-commit):** `ARCHITECTURE.md`, `HANDOFF.md`, compose comment.
- **S8 (two-lane):** `feat/phase-b1-scheduler` → `develop` → `master` with sign-off.

---

## 9. Migration / contracts / CI impact

- **Migration?** **No** — no schema change (resolution writes existing columns: `resolved_direction`,
  `resolved_at`, `auto_resolved`, added back in `006`/`008`).
- **Contracts / F1?** **No router signature change** → no `openapi.json` change → **F1 stays green**.
  (The `auto-resolve` endpoint is unchanged.)
- **`db-tests` CI:** the new real-DB test runs in the existing gated `db-tests` job — no workflow
  change needed (it already runs the whole `tests/db` dir). Stays green; gates the idempotency lock.

---

## 10. Promotion

- **Branch:** `feat/phase-b1-scheduler` off `develop`.
- **Commit split:** (1) scheduler service + settings; (2) lifespan wiring; (3) `db-tests` resolution +
  idempotency suite; (4) docs.
- **Sign-off note:** B1 complete — `resolve_open_decisions` runs on an env-gated cadence (system job,
  no per-user scope by design); idempotency + real-price resolution locked in `db-tests` (CI-gated);
  S3 proof unchanged; no schema/contracts change. `pnpm health` green. Deploy: set
  `AUTO_RESOLVE_ENABLED=true` on the API process.
- **After B1:** unblocks **B2** (skill-vs-luck scorecards consume the now-compounding resolved ledger).

---

## 11. Demonstration cohort (SETTLED REQUIREMENT) + remaining decisions

### 11.1 The sample-desk cohort — required, lands in B1, labeled (owner-decided)

**Settled:** with zero users the showcase *is* the product, and an empty calibration view hides the
entire value prop — so B1 **must** seed a believable demonstration cohort that auto-resolves into a
populated, varied calibration. **It lands in B1** (recommended over deferring to B2) because B1 already
ships the scheduler that resolves it — so the **full loop (open decision → auto-resolution → populated
reliability diagram + skill-vs-luck) is demonstrable the moment B1 lands**, which is exactly the
"showable value now" we need with no users. (B2 then *styles/surfaces* the scorecard on top of this
real, labeled data — it consumes the cohort, it doesn't need to create it.)

**Design (for honesty *and* realism):**
- Seed **open** structured decisions (varied instruments / conviction) with `anchor_price` = the **real
  historical close** at each (past) `created_at`. The B1 scheduler then resolves them; because the moves
  are real, the **outcomes are genuine hits/misses** — we are showing the *real engine working on
  labeled sample inputs*, not fabricated results. Tune the conviction/threshold spread so the resolved
  set produces a varied reliability diagram (a couple of well- and poorly-calibrated buckets) and a
  non-trivial desk readout.
- **Horizons must be ALREADY-ELAPSED (back-dated):** each decision's `created_at` is set far enough in
  the past that `created_at + horizon_days < now` **already**, with the target date inside the real
  price window (≤ 2026-06-05). So the **very first scheduler tick — which runs on boot, before the
  first sleep (§5) — resolves the whole cohort immediately** and the calibration view is populated at
  startup. **We do not wait a day** for the showcase to fill; daily is only the *standing* cadence for
  decisions that arrive later. (The `db-tests` lock proves first-tick resolution on real prices.)
- Seed into the **anonymous/sample (`user_id IS NULL`) pool**, which B3a already routes to the
  signed-out/demo calibration view — so real signed-in users never see it; they get their own empty
  ledger.

**The one hard requirement (the credibility line):** it is **labeled "sample desk / demonstration
data, not a real analyst track record"** on every surface that shows it (S6). Showing the product
working on *labeled* sample data is honest and compelling; dressing fabricated decisions as a genuine
usage history is the one thing we will not do. Label it → both compelling and honest.

**Kept separate from the engine proof:** the `db-tests` idempotency/real-resolution **lock test uses
its own tiny controlled decision**, independent of the showcase cohort — so the regression gate proves
the *engine*, not the demo data.

### 11.2 Decisions (settled by the owner)

1. **In-process, env-gated lifespan loop — CONFIRMED.** Run the scheduler **in the API process**
   (mirrors `start_ticker`), launched from the lifespan **only when `auto_resolve_enabled` is true
   (default OFF)**. **Do NOT wire the compose `worker` service** — it stays the placeholder. The
   multi-replica scale answer (Postgres advisory lock, or moving the loop to a dedicated worker) is
   **deferred**, noted as future hardening; idempotency keeps a multi-replica run correctness-safe in
   the meantime.
2. **Daily cadence — CONFIRMED.** `auto_resolve_interval_hours = 24` (prices are daily; nothing
   resolves faster than a new close). A paired price-backfill tick stays optional/opportunistic (§4).
