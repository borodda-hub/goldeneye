# Phase A3 Plan — The Validation Page ("How We Validate")

**Objective (MASTER_PLAN §4 A3 — the last unfinished Stage-A item):**
externalize `MODEL_DILIGENCE.md` into a first-class page — *honesty as
marketing*. After Phases 26→31 and the Stage-D sweep, this page can say
something no competitor can: **every claim is tested, every verdict is
published — including the failures — and the page proves itself against
live numbers.** DoD (from the master plan): page published; matches the
provenance ledger.

**Status:** plan drafted 2026-07-25 (deep recon of the design system,
honesty surfaces, and AI_BEHAVIOR constraints — file-line evidence
throughout). Build follows owner review of this plan.

---

## 1. The communication strategy (what this page argues, and how)

**The argument, in one line:** *"We publish what our models can't do —
that's why you can trust what they can."*

**Voice + register.** The app already has a sanctioned "marketing voice
inside the terminal": the serif-h2 + `GoldItalic` + `max-w-3xl` lede
pattern from `CalibrationShell.tsx:94-111`. `/validation` uses that
register for its opening and the terminal's mono/data register
(`font-mono tabular-nums`, honesty-footnote paragraphs) for everything
evidential. Numbers argue; prose introduces.

**The three credibility moves (each is a UI element, not a paragraph):**
1. **Failures first-class.** The ledger renders `❌ no edge` and
   `🚫 premise absent` rows with the same visual weight as the validated
   edge — sorted with the one real edge on top, the failures immediately
   after (never collapsed, never below a fold). A trust page that only
   shows wins is an ad; one that leads with its retirements is evidence.
2. **Pre-registration made visible.** Each probe row shows *gate locked →
   run executed* as two dated events (the gate-commit SHA vs the run
   date), plus the "re-runs in one command" command string. This is the
   detail a skeptical reader can actually verify in the repo.
3. **The page checks itself.** The "live proof" strip renders numbers the
   page does NOT control — the walk-forward coverage readout from
   `/v1/forecast/range` and the desk skill-vs-luck verdicts from
   `/v1/calibration/desk` — live, next to the ledger's claims about them.
   If calibration ever degrades, this page shows it. That asymmetric
   exposure IS the trust argument.

**Language constraints (S6 / AI_BEHAVIOR — reviewed against the recon):**
- Forbidden-phrase list applies to every string (`AI_BEHAVIOR.md:17-45`);
  highest-risk words for a "proof" page: *guaranteed/guarantee* (use the
  established "measured walk-forward, not guaranteed" construction),
  *risk-free/no risk* (use "no capital at risk"), any first-person
  recommendation.
- "No claim without provenance" applies to self-deprecating claims too —
  every ledger row carries its `synthetic | real-OOS | real-in-sample |
  methodology | collecting` label.
- Any seeded desk numbers on the page REQUIRE `<SampleDeskBanner/>`
  (§sample_data_labeling — the banner is the canonical artifact).
- Model-voice strings live in `lib/strings.ts`
  (§user_facing_strings_governance).
- The standard disclaimer renders for free — the `(app)` layout footer
  (`layout.tsx:88-94`) covers every route.

---

## 2. Information architecture (the page, top to bottom)

Route: `apps/web/app/(app)/validation/` — `page.tsx` (RSC, `try/catch`
prefetch) + `ValidationShell.tsx` (`"use client"`), mirroring
`calibration/`. Root `<div className="stagger flex flex-col gap-6">`.

1. **`<PageHeader icon={Microscope} title="How We Validate"
   subtitle="model diligence · provenance ledger" />`** (icon unused
   elsewhere; `ShieldCheck` is taken by the ledger integrity badge).
2. **Thesis section** (the sanctioned serif register): headline *"We
   publish what our models* `can't` *do."* + a 3-sentence lede: one
   validated edge (vol/range interval calibration), direction tested and
   not crowned, every verdict below re-runnable.
3. **Method strip** — 4 compact cards (gold-eyebrow card-header idiom,
   `HelpTip` on each): *Pre-registered gates* (committed before the run) ·
   *Walk-forward only* (look-ahead-safe; guarded by the cheating-model
   proof in CI) · *Real-data provenance* (synthetic results are never
   evidence) · *Bench-and-say-so* (failed gates are published and kept).
4. **THE LEDGER** (centerpiece) — the provenance table, one row per claim
   from the structured backend (see §3): verdict badge + claim + one-line
   result + provenance label + evidence (harness · n/n_eff · gate-commit →
   run-date) + doc anchor. Table idiom = `DeskCalibrationCard.tsx:121-156`
   (mono table, `text-[9px]` uppercase heads, honesty footnote below).
   Badge vocabulary (VerdictBadge shape, `border-*/40 bg-*/10` pattern):
   - `EDGE — real-OOS` (up) · `NO EDGE — real-OOS` (down-muted; styled
     factual, not alarming) · `PROMISING` (conf-medium) · `PARTIAL /
     INSUFFICIENT-N` (ink-3) · `COLLECTING` (cyan) · `METHODOLOGY`
     (ink-3) · `BENCHED` (ink-4).
   Row order: the vol/range edge first, then the no-edge directional
   family, then promising/parked, then collecting archives, then
   methodology rows.
5. **Live proof strip** — 2–3 cards of numbers the page doesn't control:
   - *Interval calibration, live:* `useRangeForecast` → cov80/cov95 +
     n_eff + forward-vol corr, labeled "measured walk-forward on real
     prices — the number the 80% band must keep earning."
   - *The tool that refuses to crown noise:* `useDeskCalibration` →
     Wilson verdicts (blind desks reading `luck` IS the demonstration);
     `<SampleDeskBanner/>` rendered above it (mandatory).
   - *Archives accumulating:* weather + curve vintage day-counts (from
     the new endpoint, §3) with their dated re-entry triggers — "what we
     can't test yet, and the day we can."
6. **Reproduce-it footer** — the honesty-footnote idiom listing the
   re-run commands (`validate_engine_oos --alt-only`, `validate_vol_real`,
   `validate_d1_vol_premium`, …) + "gates live in `docs/PHASE_*_PLAN.md`,
   committed before each run" + link to the raw `MODEL_DILIGENCE.md` on
   GitHub.

**States:** skeleton mirroring the layout (house pattern); ledger renders
from the endpoint with a mono `Loading…` fallback; live-proof cards render
`null` until their endpoints answer (the `ExpectedRange` convention — an
undeployed backend can never break the page).

---

## 3. Data architecture — the page can never drift (the "smart" part)

**Problem:** static page copy about model claims WILL drift from
`MODEL_DILIGENCE.md` (the claims SOT) — and a drifted honesty page is
worse than none.

**Design: one structured source + a CI drift-lock, live numbers fetched
not restated.**
- **`apps/api/services/validation_ledger.py`** — the ledger as typed
  constants: `LedgerRow(key, claim, verdict_kind, provenance, summary,
  evidence, harness, gate_ref, doc_anchor, updated)`. Hand-curated (rows
  are editorial judgments, not parseable markdown), ~12–14 rows.
- **`GET /v1/validation`** — `routers/validation.py` per the
  `positioning.py` idiom (router = DI + delegate, zero logic): returns
  `{rows: [...], archives: {weather_days, curve_days}, generated_at}`.
  The archive counts come from the two `count_vintage_days` repo fns
  (dev/prod truth, source-filtered to real). Not model output → no
  SafetyEnvelope needed (layout footer covers the disclaimer); every row
  carries `provenance` (the non-negotiable).
- **The drift-lock (S5, the load-bearing test):**
  `tests/test_validation_ledger.py` asserts, for every row: (a) its
  `doc_anchor` substring exists in `docs/MODEL_DILIGENCE.md`; (b) its
  `verdict_kind` is consistent with the doc row's marker (❌/✅/⏳/⚖️ …);
  (c) every `MODEL_DILIGENCE.md` ledger-table row has a corresponding
  code row (count parity) — so editing either side alone FAILS CI in the
  fast suite. The page structurally cannot outrun the doc, and vice versa.
- **Contract impact:** one new path → OpenAPI drift → regen
  `packages/contracts` + the F1 `contracts` CI job goes red→green on
  exactly this path (the established proof pattern).

---

## 4. Site integration

- **Nav:** insert at position 9 — after `Calibration`, before `Admin`
  (`SideNav.tsx:26/27` boundary): the two honesty surfaces read as a pair
  ("how good are YOUR decisions" / "how good are OUR models"). MobileNav
  inherits automatically; no scroll risk at 10 items (recon-verified).
- **Landing page** (bundled, separate commit):
  1. New **"05 · How we validate"** section between §04 (the strongest
     empirical claims — where the "prove it" reflex fires) and "Built to
     last" (renumber 05→06, 06→07): condensed 5-row ledger + `GhostCta`
     → `/validation`.
  2. `GhostCta` **"How we validate"** in the cover CTA row — honesty
     above the fold is the whole A3 premise.
  3. **A1 copy fix (due diligence):** `page.tsx:462` "the hit rates are
     honest" now overstates vs the tested-no-edge record — rewrite that
     capability to lead with calibration + point at `/validation`.
- **Cross-links from every calibrated readout** (one-line changes):
  `ExpectedRange` footnote, `DeskCalibrationCard` footnote, and
  `BacktestCard`'s honesty strip each gain a `How we validate →` link.
  The page becomes the hub those spokes already imply.
- **Walkthrough:** one step appended to `steps.ts` (+ `data-tour=
  "validation-shell"`), and fix the stale "Six more screens" copy at
  `steps.ts:80` in the same commit.
- **HelpTips:** new glossary keys in `lib/helpText.ts`: `provenance`,
  `realOos`, `walkForward`, `preRegistered`, `nEff`.

---

## 5. Build phases, gates, promotion

**A3.1 — backend + drift-lock** (S): `validation_ledger.py` + router +
`tests/test_validation_ledger.py` (drift-lock proven red→green by
deliberately desyncing once) + contracts regen. Gate: health green;
contracts job red→green on exactly the new path.
**A3.2 — the page** (M): route/shell/components (MethodStrip,
ValidationLedgerTable + badges, LiveProofStrip), skeleton, nav item, tour
step, HelpTip keys, vitest coverage (badge mapping, ledger render from a
fixture, footnote strings), **visual verification via Playwright at
390/768/1440 (the banked "run the app and look" lesson) in all themes'
token space (token-only styling — zero hex)**.
**A3.3 — landing + cross-links** (S): the new section, cover CTA, the A1
copy fix, the three spoke links. S6 claims-gate checklist run over every
string (forbidden-phrase grep + provenance check).
**Promotion:** each phase `feat/phase-a3-*` → develop (CI incl. contracts
+ db-tests) → master with owner sign-off; page verified live in prod
(real coverage numbers rendering) before closing A3 in `MASTER_PLAN.md`.

**Effort:** ~1 focused session (A3.1+A3.2), +half for A3.3.
**Dependencies:** none — all data sources exist and are typed.
**Out of scope (deliberately):** the whole-app UI audit (owner: "that's
later"); D1b design review (separate, now scheduled per the upgraded
PROMISING verdict); any new predictive claim.

## 6. §7.4 checklist

`pnpm health` · S3 untouched (read-only page; no model/resolution path) ·
S4 n/a (no claim changes — the page RENDERS the ledger; the drift-lock
enforces fidelity) · S5 drift-lock + component tests · **S6 is the whole
point** — claims-gate review on every string · S7 this plan +
`MASTER_PLAN` A3 status in-commit · S8 two-lane promotion.
