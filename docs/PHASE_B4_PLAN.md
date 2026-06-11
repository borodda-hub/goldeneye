# docs/PHASE_B4_PLAN.md — Stage B4: Decision/audit ledger + observability

_Plan-mode output per `MASTER_PLAN.md §7.2`. **Plan only — no code until owner sign-off.**_
_Branch (when built): `feat/phase-b4-ledger-observability`. Backend + frontend promote together._

---

## 1. Objective + DoD

**Objective.** Two bundled deliverables from `MASTER_PLAN.md §4 / B4`:
1. **Immutable decision/audit ledger** — a tamper-evident, append-only record of every decision
   and its lifecycle, surfacing the *"at the moment of decision, here is exactly what you knew"*
   view (the compliance story). The structured-decision machinery already *captures* rich context
   at write time (§2.1); B4 turns that into a **true immutable audit trail** (append-only storage
   the app cannot rewrite) and a **read surface**.
2. **Minimal observability** — the smallest genuinely-useful layer now that the app is multi-tenant:
   structured request logging with a request-id, a handful of exported metrics, and
   **safety-violation alerting** (activating the dormant `Alert` table). **Not** a full APM/OTel
   buildout.

**Definition of Done** (from `MASTER_PLAN.md §4 / B4`, sharpened):
- An **append-only `decision_ledger_events` table** records `created` / `resolved` / `amended`
  events; **immutability is DB-enforced** (a trigger rejects `UPDATE`/`DELETE`), not convention,
  and **tamper-evident** (per-decision hash chain a verifier can check).
- `GET /v1/ledger` + `GET /v1/ledger/{decision_id}` render the per-user audit trail, **scoped by
  `user_id`** with by-id 404 ownership (B3 invariant) — no cross-user leak.
- Safety violations **populate the existing `Alert` table** (kind=`safety_violation`, with
  `user_id`) and increment a counter; structured request logging + a `/v1/metrics` endpoint export
  the minimal metric set.
- `pnpm health` green (S2); contracts CI red→green for the new endpoints (F1); the immutability +
  isolation locks live in the **gated `db-tests` suite** (S5); docs in-commit (S7).
- **S3 untouched** — no model or resolution *logic* changes; the ledger only *observes*.

---

## 2. Verified facts (read this session — verify, don't infer; `[V]` = confirmed in code)

### 2.1 What is ALREADY captured at decision time (the journal is rich but mutable)
- `[V]` `apps/api/models/orm/journal.py` — `UserDecisionJournal` already snapshots **write-once at
  create**: `hypothesis`, `evidence` (JSONB), `confidence_pct`, `planned_action`, `risk_factors`,
  `invalidation_criteria`, `predicted_direction`, `horizon_days`, `threshold_pct`, `anchor_price`,
  `thesis_id_at_write`, `thesis_conviction_at_write`, `created_at`, `user_id`, `instrument_id`.
  (migrations `006_journal_calibration`, `007_decision_capture`.)
- `[V]` **Mutated post-creation**: `outcome`, `reflection`, `llm_review`, `resolved_direction`,
  `resolved_at`, `auto_resolved`. The journal row is **live mutable state, not an append-only
  record** — `apps/api/repos/journal.py::update()` allow-lists `{outcome, reflection, llm_review,
  resolved_direction}`; resolution overwrites `resolved_*` in place (`auto_resolution.py:127-131`).
  **Once a mutable field changes, the prior value is lost** — no history.
- `[V]` **Not captured today:** the *system's* state at decision time — the ensemble forecast
  (direction / agreement / derived confidence), the vol band / expected range, the vol regime, the
  model lineup, the LLM safety envelope are **not** snapshotted onto the decision. Only the user's
  inputs + thesis snapshot + anchor price are. (The `llm_review` JSONB holds a `SafetyEnvelope`
  *for the review text*, not the forecast envelope.) → This is the gap "here is exactly what you
  knew" must close.
- `[V]` **Immutability is convention only.** Write-once is enforced by the repo allow-list
  (`journal.py:65-70`); nothing at the DB level prevents an `UPDATE`/`DELETE` on any column.
  `tests/...test_journal_calibration_columns.py` proves the allow-list drops disallowed patches —
  but that is app convention, not a DB guarantee.

### 2.2 The two write-convergence points (where ledger events must be appended)
- `[V]` **Create** — `apps/api/routers/journal.py::create_entry()` (`:101-164`): builds `data`,
  calls `journal_repo.create()` (`:142`), best-effort LLM review, `session.commit()` (`:163`). The
  `decision_created` event appends here, **in the same transaction**, with `scope = user.id or None`
  (`:107`). This router also holds the live context to snapshot the system state.
- `[V]` **Resolve** — `apps/api/services/auto_resolution.py::resolve_open_decisions()`
  (`:80-134`): sets `resolved_direction/resolved_at/auto_resolved` on each elapsed decision
  (`:127-129`), `session.flush()` (`:133`). The `decision_resolved` event appends per resolved
  decision here (scope = the decision's own `user_id`). **The resolution *logic* is not touched** —
  the append is a post-decision side-effect that cannot change what gets resolved (S3-safe).
- `[V]` **Manual amend/resolve** — the journal PATCH route + `journal_repo.update()` allow-list
  (`outcome`/`reflection`/`resolved_direction`). A `decision_amended` (or `resolved`) event appends
  here, recording old→new for the changed mutable fields (this is where today's history-loss is
  fixed).

### 2.3 Isolation machinery to reuse (B3 — already live)
- `[V]` Personal-artifact routers resolve the requester via `Depends(get_optional_user)`, thread
  `scope = user.id or None`, filter on it, and enforce by-id ownership `row.user_id != scope → 404`
  (e.g. `journal.py:107`, `:197-199`). The ledger endpoints **reuse this verbatim**. Anonymous /
  Clerk-off demo → `scope=None` → shared NULL pool (unchanged).

### 2.4 Observability — current state (essentially nothing)
- `[V]` **No Sentry / OTel / metrics / structured logging.** `pyproject.toml` has none of
  `sentry-sdk`, `opentelemetry-*`, `prometheus-client`, `structlog`. `SENTRY_DSN` + `LOG_LEVEL`
  exist in `.env` but are **not** settings fields and are unused. Logging is ad-hoc
  `logging.getLogger(__name__)`; the only middleware is CORS (`src/main.py:68-74`).
- `[V]` **The `Alert` table already exists and is unused.** `apps/api/models/orm/alerts.py`
  (`id, created_at, user_id, kind, severity, payload JSONB, read, acknowledged`), created in
  `002_relational` (no new migration needed for it). `apps/api/repos/alerts.py` is read/ack-only;
  **nothing creates an Alert** (grep `Alert(` → only the model). `GET /v1/admin/alerts` +
  `/v1/admin/alerts/{id}/ack` exist, **admin-gated** (`get_current_user`, B3b). → B4 just
  *populates* this on safety violations.
- `[V]` **Safety violations are detected but not recorded.** `services/llm_explainer.py::
  _call_with_safety_check()` retries once then raises `SafetyViolation`; `src/main.py:78-89` maps it
  to HTTP 500 with no persistence/alert. `services/safety.py::scan_for_forbidden()` is the detector.
- `[V]` `GET /v1/health` is liveness-only (`src/main.py:118`). Migration head is **`010`** (→ B4 =
  `011`). `cryptography` is already a dep; `hashlib` (stdlib) covers the hash chain — **no new dep
  needed for the ledger**.

---

## 3. Design — the audit ledger (addresses the owner's questions 1 & 3)

### 3.1 New table, not extended rows — and *why*
**B4 adds a new append-only table `decision_ledger_events`; it does NOT extend the journal row.**
Reason: the journal row is, by design, mutable live state (resolution + outcome/reflection edits in
place). Adding more columns to it cannot produce an *append-only* trail — the row still mutates and
still loses history. A true audit trail must be a **separate, insert-only event log** that shadows
the journal. The journal stays exactly as-is (no behavior change); the ledger is its immutable
record.

**Schema (`011_decision_ledger`):**
| Column | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `seq` | BIGSERIAL | global monotonic append order (gap-tolerant) |
| `decision_id` | UUID FK→`user_decision_journals.id` `ON DELETE RESTRICT` | the decision this event belongs to |
| `user_id` | UUID NULL FK→`users.id` `ON DELETE RESTRICT` | **copied at append time** for scoping (NULL = anonymous pool) |
| `event_type` | TEXT CHECK in (`created`,`resolved`,`amended`) | |
| `occurred_at` | TIMESTAMPTZ | domain time of the event (decision `created_at`; resolution `resolved_at`; amend wall-clock) |
| `recorded_at` | TIMESTAMPTZ default `now()` | append wall-clock |
| `source` | TEXT NOT NULL default `live` CHECK = `live` | provenance is always live-captured — there is no `backfill` value, structurally enforcing §3.4 (no fabricated history) |
| `payload` | JSONB NOT NULL | the snapshot (§3.3) |
| `prev_hash` | TEXT NULL | row_hash of the previous event for this `decision_id` |
| `row_hash` | TEXT NOT NULL | `sha256(canonical(prev_hash, decision_id, event_type, occurred_at, payload))` |

Indexes: `(user_id, decision_id, seq)` for the scoped read; `(decision_id, seq)` for the per-decision chain.

### 3.2 Immutability — DB-enforced, not convention (owner question 1)
Three layers, strongest first:
1. **DB trigger (the enforcement).** Migration creates a trigger function that `RAISE EXCEPTION`s on
   `UPDATE` or `DELETE`, attached `BEFORE UPDATE OR DELETE ON decision_ledger_events`. **`INSERT` is
   the only operation the database permits** — a buggy or compromised service issuing an
   `UPDATE`/`DELETE` is rejected by Postgres, not by app code. This is the literal answer to "no
   UPDATE/DELETE path, not just convention."
2. **No app mutation path (convention, defense-in-depth).** `apps/api/repos/ledger.py` exposes only
   `append_event(...)` + read methods — there is no update/delete method to call.
3. **Hash chain (tamper-evidence).** Each event's `row_hash` chains off the previous event's hash
   for that decision. A `verify_chain()` function (and a `GET /v1/ledger/{decision_id}/verify` or a
   field on the read) recomputes the chain and flags any break — so even a *superuser* edit that
   bypasses the trigger (direct SQL outside the app) is **detectable**. Tamper-*evident* on top of
   tamper-*resistant*. (We do **not** claim cryptographic notarization / external timestamping —
   that's out of scope, §6.)

### 3.3 The "at the moment of decision, here is exactly what you knew" view
The `created` event's `payload` captures, in one immutable blob:
- **User inputs (from the journal write-once fields):** hypothesis, evidence, confidence_pct,
  predicted_direction, horizon_days, threshold_pct, anchor_price, planned_action, risk_factors,
  invalidation_criteria, thesis snapshot (`thesis_id_at_write`, `thesis_conviction_at_write`).
- **System context at that instant (the gap §2.1 closes):** the ensemble forecast (direction,
  agreement N-of-M, derived envelope confidence), the vol band / expected range + estimator, the
  vol regime, the model lineup identifiers, and the forecast `as_of`. Captured by **reusing the
  same `ensemble` + `vol_range` computation the signals/forecast endpoints already call** — no new
  model, no new calibration feature (§6 scope).
  - **Missing-context is RECORDED, never silently omitted.** The capture is wrapped (a forecast
    hiccup never blocks a decision write), but on failure the payload does **not** drop the field —
    it records the *absence* explicitly: `system_context: {captured: false, reason: "<unavailable:
    ...>"}` (e.g. `"unavailable: no forecast for instrument at as_of"`). An audit log that silently
    omits context it couldn't capture is dishonest — the ledger must show *that* it didn't know, and
    *why*, not present a hole as if context never applied. Every `created` event therefore has a
    `system_context` key: either the captured snapshot or an explicit recorded absence with a reason.

The `resolved` event payload records: outcome (hit/miss/neutral), `resolved_at`, `auto_resolved`,
the realized close + anchor + computed move, and the deadband used. The `amended` event records the
field name + old→new value.

The **view** (`GET /v1/ledger`, `GET /v1/ledger/{decision_id}`) returns each decision with its
ordered event timeline + a `chain_ok` boolean from the verifier.

### 3.4 No backfill — forward-only is the *correct* answer, not a deferral
**Pre-B4 decisions have no ledger entry, by design.** You cannot honestly backfill an audit ledger:
reconstructing weeks-old decision-time state (the forecast, regime, prices you'd *have to* re-derive
after the fact) and recording it as if it had been captured live is **fabricated provenance** — the
exact dishonesty an audit trail exists to prevent. The ledger therefore **accrues from the B4
deploy forward only**; decisions created before B4 are shown plainly as **"no immutable record (pre-
ledger)"** — never with a synthesized event. The `source` column (`live` only, in practice) and this
rule make the absence explicit rather than papered over. (This is a hard rule, not an optional
trade-off — see §6.)

---

## 4. Design — observability (addresses owner question 2: smallest useful, not APM)

Three components, each high-value-per-line; explicitly **not** a full OTel/APM buildout.

1. **Safety-violation alerting (the compliance-critical one — activates dormant infra).** When
   `_call_with_safety_check` blocks after retry, **create an `Alert`** (`kind="safety_violation"`,
   `severity="error"`, `payload={task, output_snippet[:200]}`, `user_id` from request context if
   available) *before* raising `SafetyViolation`, and increment `safety_violations_total`. The
   existing admin `/v1/alerts` view surfaces them (already admin-gated). Near-zero new infra; the
   table + repo + endpoint already exist.
2. **Structured request logging + request-id (the "span" substitute).** One ASGI middleware:
   assign/propagate an `X-Request-ID`, time the request, emit one structured log line
   (`method, route, status, duration_ms, request_id, user_id?`). Add a `log_level` setting +
   `logging.dictConfig` at startup. This is the minimal multi-tenant traceability — *not*
   distributed tracing. (Full OTel spans deferred, §6, with a re-entry note.)
3. **Metrics export (the DoD's "metrics exported").** Add `prometheus-client` (small, standard,
   scrape-ready, no collector needed) + a `GET /v1/metrics` endpoint (Prometheus text format). Metric
   set kept tiny and genuinely useful: `http_requests_total{method,route,status}`,
   `http_request_duration_seconds`, `safety_violations_total`, `auto_resolutions_total{outcome}`,
   `ledger_events_total{event_type}`. (Zero-dep hand-rolled counters are an alternative if the owner
   prefers no new dep — flagged as a judgment call.)

**Observability isolation:** alerts carry `user_id`; the admin alerts view is desk-wide + admin-gated
(unchanged). Metrics are aggregate, no PII. The per-user ledger is the only user-scoped surface and
follows §2.3.

---

## 5. Change set (by lane — promotes backend + frontend together)

### 5.1 Schema (`infra/migrations/versions/011_decision_ledger.py`)
- Create `decision_ledger_events` (§3.1) + indexes + the immutability trigger function & trigger
  (§3.2). No change to existing tables. Update `docs/SCHEMA.md` in-commit (S7).

### 5.2 Backend (`apps/api`)
- **`models/orm/ledger.py`** — the `DecisionLedgerEvent` ORM.
- **`repos/ledger.py`** — `append_event(...)` (computes `prev_hash`/`row_hash`), `list_for_user(scope)`,
  `get_for_decision(decision_id, scope)`, `verify_chain(decision_id)`. **No update/delete methods.**
- **`services/ledger.py`** — `build_created_payload(...)` (journal fields + best-effort system-context
  via existing `ensemble`/`vol_range`), `build_resolved_payload(...)`, `build_amended_payload(...)`,
  `canonical_hash(...)`.
- **Hook the three convergence points (§2.2):** `journal.py::create_entry` (append `created`),
  `auto_resolution.py::resolve_open_decisions` (append `resolved` per row — logic untouched), the
  journal PATCH route (append `amended`/`resolved`).
- **`routers/ledger.py`** — `GET /v1/ledger`, `GET /v1/ledger/{decision_id}` (B3-scoped, by-id 404),
  typed Pydantic response models → contracts.
- **Observability:** request-id/timing ASGI middleware in `src/main.py`; `log_level` + `sentry_dsn`*
  settings + `dictConfig`; populate `Alert` on safety violation in `llm_explainer.py`; metrics
  registry + `GET /v1/metrics`; counters incremented at the hook points. (*Sentry stays a settings
  field only — wiring deferred, §6.)

### 5.3 Frontend (`apps/web`)
- A **Decision Ledger view** (under the calibration/journal area): per-decision immutable timeline —
  "what you knew at decision" (the `created` snapshot) → resolution, with a `chain_ok` integrity
  badge. Honest framing (no advice language; S6). Types regenerated from contracts; hand-written
  `lib/api.ts` types mirror the generated `LedgerResponse`.

### 5.4 Dependencies
- `prometheus-client` (small) — the only new runtime dep. `hashlib` (stdlib) for the chain. No
  sentry-sdk / OTel deps in B4.

---

## 6. Out of scope (explicit — do not let it creep)

- **B5 (cross-asset).** No per-asset config, no second asset class, no `registry.py` de-commoditizing.
- **New calibration / model features.** No new scorecards, verdicts, voters, ensemble changes, or
  model/resolution-logic changes. Capturing the forecast *snapshot* reuses existing computation and
  is read-only — it is **not** a new model.
- **Full APM / distributed tracing.** No OpenTelemetry SDK/exporter/collector, no Grafana/dashboards,
  no Jaeger. Request-id structured logs are the lightweight substitute; OTel is a tracked re-entry
  item.
- **Sentry wiring.** A `sentry_dsn` settings field may be added for completeness, but
  `sentry_sdk.init` wiring + the dep are deferred (cheap later add; not needed for the in-house trio).
- **Cryptographic notarization.** The hash chain is tamper-*evident*, not externally-notarized; no
  third-party timestamping authority.
- **Ledger backfill** of pre-B4 decisions — **forbidden by design** (§3.4), not deferred. The ledger
  accrues forward-only; pre-B4 decisions show "no immutable record (pre-ledger)." Synthesizing
  historical events would be fabricated provenance, so the `source` column structurally cannot mark
  a row as backfilled.
- **Changing the journal's mutability model** or the auto-resolution engine's resolution logic.

---

## 7. Impact (owner question 5)

- **Migration:** **YES** — `011_decision_ledger` (new table + indexes + immutability trigger). Run
  `make migrate`; update `SCHEMA.md` same commit (S7). The `Alert` table already exists — **no
  migration for alerting**.
- **Contracts:** **YES** — new `GET /v1/ledger` + `GET /v1/ledger/{decision_id}` with typed response
  models → F1 contracts CI red→green; regen `packages/contracts` (compact, per the B2 lesson). The
  `/v1/metrics` endpoint returns Prometheus text (not JSON) → not a typed contract. No change to the
  existing `/v1/journal` or `/v1/admin/alerts` contracts.
- **S3 (look-ahead invariant):** **Not touched.** No model or resolution *logic* changes — the
  ledger only observes (appends events; reads current forecast state to snapshot it). The
  cheating-model proof (`tests/test_backtest_lookahead.py`) is unaffected; state this explicitly in
  the commit.
- **Isolation (owner question 3):** the ledger read is `user_id`-scoped with by-id 404 (B3 pattern,
  §2.3); the append copies `user_id` from the decision; locked by an HTTP A-vs-B test (S5).

**Test-locked (S5):**
- **Immutability (gated `db-tests`):** an `UPDATE` and a `DELETE` against a ledger event each **raise
  at the DB level** (the trigger) — the core guarantee.
- **Tamper-evidence (gated `db-tests`):** `verify_chain` returns ok for an intact chain and **detects**
  a payload mutated out-of-band.
- **Append-on-lifecycle (gated `db-tests`):** a decision create appends exactly one `created` event
  (with the snapshot); auto-resolution appends a `resolved` event; a manual outcome edit appends an
  `amended` event.
- **Recorded-absence (mocked `test-api`):** when system-context can't be captured, the `created`
  event's payload carries `system_context: {captured: false, reason: ...}` — i.e. the key is
  **present with an explicit reason**, never missing. Locks the "never silently omit context" rule.
- **Isolation (gated `db-tests`, HTTP):** B/anon cannot read A's ledger (404 by-id; lists scoped);
  anonymous demo still works.
- **Safety-violation alerting (mocked `test-api`):** a forbidden phrase surviving retry creates an
  `Alert` (kind=`safety_violation`, correct `user_id`) and increments the counter.
- **Observability (mocked `test-api`):** the middleware sets `X-Request-ID`; `/v1/metrics` returns the
  registered metrics.

---

## 8. Gates (S1–S8 — applicability)

- **S1 (WIP=1):** B4 is the single active primary thread; promoted to `master` before B5/C3 start.
- **S2 (full gate):** `pnpm health` green end-to-end.
- **S3:** preserved — no model/resolution logic change (explicit in §7 + commit).
- **S4 (provenance):** B4 makes no *predictive* claim, so no `MODEL_DILIGENCE.md` ledger row; but the
  "what you knew" snapshot must label captured-vs-not (`system_context.captured`) and backfilled-vs-live
  (`source`) honestly — that *is* the integrity discipline here.
- **S5 (test-lock):** the immutability + tamper-evidence + isolation locks above (gated suite).
- **S6 (claims gate):** the ledger UI carries no advice/certainty language; it presents recorded facts
  + an integrity badge. No forbidden phrases.
- **S7 (docs in-commit):** `SCHEMA.md` (new table + trigger), `API_CONTRACTS.md` (new endpoints +
  the alerting/observability note), `ARCHITECTURE.md` (correct the "no observability" line; add the
  ledger + the minimal-observability tier). `MODEL_DILIGENCE.md` unchanged.
- **S8 (two-lane):** `feat/phase-b4-ledger-observability` → `develop` → owner-signed `master`.

---

## 9. Promotion

- **Branch:** `feat/phase-b4-ledger-observability`.
- **Sequence:** migration `011` → ledger ORM/repo/service + the three hooks → ledger endpoints →
  observability (middleware/metrics/alerting) → contracts regen → frontend ledger view →
  `pnpm health` + gated `db-tests` (immutability/tamper/isolation) green → push, PR to `develop`
  (CI incl. `contracts` + `db-tests` green) → merge → **owner sign-off** → fast-forward `master`.
- **Live-verify before promotion:** create a decision → confirm a `created` event with the snapshot;
  auto-resolve → confirm a `resolved` event; attempt an `UPDATE`/`DELETE` → DB rejects; the ledger
  view renders the timeline + `chain_ok`; trigger a safety violation → an `Alert` appears in
  `/v1/admin/alerts`; `/v1/metrics` returns counters. (Run the app and look — the banked lesson.)
- **Post-promote:** update `HANDOFF.md` (B4 done; next = B5/C3) + `project_phase_state.md`.

---

## 10. Owner decisions (RESOLVED — locked into the plan above)

1. **System-context capture in the `created` snapshot — INCLUDE NOW** (§3.3). It's the heart of the
   compliance story and touches no model logic. **Refinement (locked):** missing context is
   **recorded as an explicit absence with a reason** (`{captured: false, reason: "..."}`), never
   silently omitted — every `created` event carries a `system_context` key.
2. **Metrics dependency — `prometheus-client`** (§4.3). Standard, scrape-ready, no collector.
3. **Backfill — NONE, forward-only by design** (§3.4). Not a deferral: an audit ledger cannot be
   honestly backfilled (fabricated provenance), so pre-B4 decisions have **no ledger entry by
   design** and are shown as "no immutable record (pre-ledger)." The `source` column structurally
   forbids a non-`live` value.
