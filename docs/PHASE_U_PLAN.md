# Phase U Plan — UI Hardening ("premiere" pass)

**Objective (owner directive 2026-07-27):** the app is effectively unusable
below ultrawide widths — cards overlap, prose clips mid-sentence, columns
collapse — and typography is too small and inconsistently treated. The
design language is good; the execution is single-width-tuned. Phase U makes
layout correctness *enforceable*, then fixes structure, type, and hierarchy.

**Diagnosed root causes (evidence: dashboard screenshots at 1280/1440):**
1. **Fixed *pixel* pane widths at ≥lg** (`ResizableSplit`/`ResizableColumn`
   with persisted px): the June responsive pass stacks them below `lg`, but
   above it the pixels still rule — narrower-than-tuned screens overlap
   (Recent Events drawn OVER Futures Curve at 1280; storage card crushed to
   a letter-wide sliver), wider screens leave dead gutters.
2. **Missing `min-w-0` + stray `whitespace-nowrap`** on text-bearing
   flex/grid children → pathological wraps ("Henry Hub Natural Gas" one
   word per line) and neighbor collapse.
3. **Fixed-height prose cards** → the Directional Bias narrative clips
   mid-word with no clamp/fade/scroll.
4. **Micro-typography:** 8–10px tracked uppercase labels everywhere; three
   competing card-header idioms.

## The four steps (each its own branch/PR, promoted separately)

**U0 — the evidence harness** *(this PR)*. `apps/web/scripts/ui-audit.mjs`:
Playwright sweep of every page × widths 390/768/1024/1280/1440/1680/1920,
producing screenshots + a programmatic defect report per page/width:
- **overlap**: pairwise bounding-rect intersection between visible card
  surfaces (`bg-surface-1` elements, ancestor pairs excluded);
- **h-overflow**: any scroll container whose content exceeds it horizontally
  without an explicit `overflow-x-auto`;
- **clipped prose**: text blocks whose scrollHeight exceeds clientHeight
  without a scroll/clamp affordance;
- **crushed columns**: text-bearing elements squeezed below readable width.
Manual gate (needs the running stack — the `validate_*` posture), exit
non-zero on defects. **DoD for every subsequent UI PR: the audit passes at
all desktop widths for the touched pages.** Baseline run committed to this
plan as the red state.

**U1 — kill the pixel layout (dashboard first).** Fluid grid
(`minmax`/`fr`) replaces fixed-px panes at ≥lg; `min-w-0` sweep;
`whitespace-nowrap` only on true chips; prose cards get natural flow or
deliberate `line-clamp` + expand. Acceptance: U0 clean for /dashboard at
1024→1920 (and no mobile regression at 390/768).

**U2 — one type system.** A hard scale codified in
`FRONTEND_COMPONENTS.md §tokens` (also fixing its stale hexes): page hero
(serif) · one **`CardHeader` component** replacing the three inline idioms ·
body 13–14px · meta 11px mono · **10px floor — nothing smaller ships**.
Migrate all cards; `tracking-eyebrow` reserved for ≥10px.

**U3 — density + hierarchy, page by page.** Explicit hierarchy per page
(hero → evidence → context); wide screens spend slack on content, not
gutters. Dashboard, then Signal Lab, then the rest — one page per PR with
before/after audit matrices.

## Gates (§7.4)

Health green per PR · U0 audit clean for touched pages (the new UI DoD) ·
no backend changes anywhere in Phase U (S3/S4 untouched) · S7 docs
in-commit (this plan per-step status; FRONTEND_COMPONENTS in U2) · S8
two-lane promotion per step.

## Status

- U0: ✅ built + baseline recorded (see §baseline below).
- U1: ✅ **SHIPPED 2026-07-27 — 103 → 63 defects; failing cells 22 → 10;
  /dashboard CLEAN at all 7 widths** (was defective at every width).
  What fixed it: (1) `ResizableSplit` is now CONTAINER-aware — it measures
  its own width with a ResizeObserver, clamps the persisted px pane at
  RENDER time (not just during drag), and stacks when two panes honestly
  can't fit; (2) rails re-gated (watchlist ≥2xl, paper rail ≥xl via a new
  `minViewport` prop) and the shell's row direction aligned to match —
  a stacked full-width rail inside a horizontal row was the 8px-column
  bug; (3) the Directional Bias narrative scrolls WITHIN its card
  (envelope collapsed by default) instead of spilling 521px; (4) HeaderRow
  wraps + truncates the instrument name (no more 40px one-word column);
  (5) the TopBar progressively discloses (theme ≥sm, onboarding chips
  ≥md) — this alone cleared the 390px h-scroll on ALL TEN pages;
  (6) PriceMiniChart's toolbar wraps at narrow widths.
  Remaining 63 defects are U3 scope: /signals spills (model grid +
  calibration card, 390–1680), /paper table crush (390+1024),
  /scenarios@390, /calibration@390.
- U2: ✅ **SHIPPED 2026-07-27 — one type system, 7/10 pages fully clean;
  app 103 → 60 defects.** What changed: (1) **the 10px floor** — every
  `text-[8px]`/`text-[9px]` in the app promoted (53 instances,
  zero remain); (2) **one canonical card-title idiom** —
  `font-mono text-[11px] uppercase tracking-eyebrow text-accent` — applied
  to every card `h2`/`h3` (the ~10 old ink-3/`tracking-widest` stragglers
  converted; all tracked eyebrow labels bumped 10→11px for readability);
  sub-labels stay ink-3/ink-4 BY DESIGN (contrast is the hierarchy);
  (3) codified in `FRONTEND_COMPONENTS.md §tokens` (+ the stale-hex note:
  token NAMES are the contract, themes.ts/globals.css are the values);
  (4) opportunistic geometry fixes the type bump surfaced: PageHeader
  subtitle truncates; the bias card's redundant right-side confidence
  label removed (was duplicating the ConfidenceBar AND spilling 22px);
  instrument-switcher name capped at 88px below `sm` (killed the last 5px
  mobile h-scroll); CalibrationSummary grid responsive.
  **Clean at all 7 widths: dashboard, chart, journal, ledger, calibration,
  validation, admin.** Remainder (U3): /signals spills (model grid +
  calibration card, 390–1680), /paper table crush (390+1024),
  /scenarios@390.
- U3: pending.

## §baseline — first full run (2026-07-27): **103 defects across 22 page/width cells**

The harness names the culprits precisely (`.ui-audit/report.json`):
1. **Directional Bias card spills 521px of prose below its box at EVERY
   width — including 1920.** The single worst defect; the owner's original
   report. (Fixed height + overflow-visible + unclamped AI narrative.)
2. **Fixed-px pane crush at 1024–1280:** Futures Curve card squeezed to
   **2–26px wide**, Working Gas in Storage to 8px, the price chart pane to
   8px — the `ResizableSplit` pixel system refusing to shrink.
3. **`Henry Hub Natural Gas` renders in a 40px-wide flex child** (one word
   per line) at ≤1280.
4. **Signal Lab at 1280:** all four model cards + Model Calibration spill
   27–90px right; `main` scrolls horizontally (grid children missing
   `min-w-0`).
5. **Paper at 1024 AND 390:** table datetime cells crushed to 73px
   (wrapping) — the table needs an overflow wrapper/responsive columns.
6. **EVERY page h-scrolls at 390: the shared TopBar forces ~760px min
   width** (chips row: Getting Started + Tutorial + instrument select +
   sign-up — the June "trim chips below sm" deferral, never done). This is
   the "much less mobile" root cause, and it is CHROME, not per-page.
7. Scenarios@390: 10 crushed columns (shock-builder grid).

**U1 scope locked from this data:** (a) the Directional Bias clamp,
(b) the dashboard pixel-pane replacement, (c) the 40px title child,
(d) the shared TopBar mobile overflow (chrome — benefits all 10 pages).
Signals/paper/scenarios cells are U3 sweeps, driven by the same report.
