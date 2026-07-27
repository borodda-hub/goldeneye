# Phase A4 — The About Page (white-paper methodology document)

_Committed before build, per the plan-before-code convention. Owner directive: "develop an
about section that fully explains the platform's methodology, architecture, value in white
paper level detail."_

## What it is

A standalone long-form document at **`/about`** — the platform's white paper. Where the
landing page *pitches* and `/validation` *proves*, `/about` **explains**: the full
methodology, the architecture, and the value thesis, in the depth a professor, an
investor's technical diligence, or a serious user would want.

## Where it lives (and why)

- **Route: `apps/web/app/about/page.tsx`** — a landing-sibling (OUTSIDE the `(app)` shell).
  A white paper is a document, not a working screen; it gets the landing's serif/scholarly
  container, not the terminal's dense chrome. Server component, zero client JS beyond the
  shared account chrome.
- **Not in the SideNav.** The nav is for working screens. Integration instead:
  - Landing chrome bar: "About" link next to "Enter Terminal".
  - Landing cover CTAs: "Read the white paper" ghost CTA.
  - Landing §06 (architecture) links into `/about#architecture`.
  - `/validation` header cross-links ("Full methodology →"); `/about` links back to
    `/validation` everywhere a claim is condensed.
- **Sticky mini-TOC** (anchor links, `hidden xl:block`) so a 3,000-word document stays
  navigable; plain stacked flow below xl. Every section gets an `id` for deep links.

## Design language

Reuses the landing idioms exactly (Eyebrow + numbered sections, GoldRule dividers, serif
display headings with `GoldItalic`, `max-w-[68ch]` body prose, mono eyebrow labels, token
colors only). White-paper additions:
- An **abstract block** up top (serif italic, the one-paragraph honest summary).
- **Pull-quote rules** for the doctrine statements (e.g. the provenance rule) rendered as
  bordered blockquotes.
- A **stack table** and an ASCII-free architecture diagram built from bordered grid cells
  (no images, no external assets).
- The §disclaimer string verbatim in the footer (the page discusses forecasts → mandatory).

## Content outline (sections are the contract)

1. **Abstract** — what Goldeneye is (research + paper-trading terminal), the one validated
   edge (calibrated vol/range bands), the honest headline (direction: tested, no edge),
   and the thesis: calibration infrastructure over prediction theater.
2. **01 · Positioning** — what it is / what it is not (no broker, no advice, no execution).
3. **02 · The problem** — outcome-worship vs decision quality; overconfidence invisible
   until scored; why calibration is the actionable signal.
4. **03 · Methodology doctrine** — the five commitments, each with its enforcement
   mechanism named: (a) no claim without provenance (`MODEL_DILIGENCE.md` rule);
   (b) pre-registered gates committed to git before probes run; (c) walk-forward,
   look-ahead-safe everything (as-of chokepoints, cheating-model CI proof);
   (d) failures published at full weight (the ledger keeps FAIL rows forever);
   (e) drift-locks — CI fails if code and published claims diverge.
5. **04 · The forecast engine** — 4 directional voters (MA, Holt, factor composite,
   trained walk-forward logreg) + ensemble w/ agreement-derived confidence + vol-regime
   context + per-asset-class config; and the honest frame: every directional model
   real-OOS tested, none earned a claim → direction ships as labeled views.
6. **05 · The volatility & range engine** — the validated edge: EWMA + log-HAR (default),
   empirical fat-tail band quantiles; coverage 78–81% (80% band) and 93–95% (95% band)
   across 6 commodities, ~10y real walk-forward; table-stakes honesty (vol autocorrelation
   is known physics — the moat is calibration + presentation).
7. **06 · The data layer** — protocol adapters (mock-first, real drop-ins: delayed market,
   EIA, CFTC, NWS, RSS), observed-vs-configured provenance, symbol-scoped as-of context,
   and the immutable vintage archives (weather + curves) accumulating toward dated
   re-entry gates.
8. **07 · Decision intelligence** — journal → auto-resolution → reliability diagram;
   hash-chained append-only decision ledger; skill-vs-luck Wilson verdict (refuses to
   crown noise); DQ Coach + devil's advocate; the sample-analyst honesty banner.
9. **08 · The AI layer** — where LLMs are used (summarize/explain/narrate/review/coach),
   and the containment: single call-site module, persona + forbidden phrases, safety
   envelope on every output, instrument-identity hardening.
10. **09 · Architecture** (`#architecture`) — four tiers, stack table, OpenAPI-generated
    contracts, testing/CI shape (health gate, DB-integration + contract drift lanes,
    UI audit harness, drift-lock tests).
11. **10 · Results** — the condensed verdict table (same idiom + data as the landing's
    §05 sample, explicitly dated "as of 2026-07") linking to `/validation` for the live
    drift-locked ledger.
12. **11 · Limitations & roadmap** — no directional edge; vol edge is table-stakes;
    hand-set cross-asset configs unvalidated; archive-gated re-entries with dates
    (weather ~Jan 2027, D1 re-run ~Jul 2027, cross-sectional carry ~mid-2028).
13. **Footer** — §disclaimer verbatim + links (terminal, validation, repo docs).

## Truth discipline

- Every number on the page must trace to `MODEL_DILIGENCE.md` (the claims SOT) and is
  dated. The page carries a standing pointer: live numbers live on `/validation`
  (drift-locked); this document is the dated narrative.
- No forbidden phrases; direction framed as views; nothing "production-grade" beyond what
  ARCHITECTURE.md §12 concedes is out of scope.
- ARCHITECTURE.md §6 still described the issue-#10 tick pin as current — corrected in this
  same arc (docs-accuracy prerequisite for citing it).

## Verification (standing DoD)

`pnpm health` exit 0 · `ui:audit` clean for `/about` (add it to the harness page list) +
landing · visual pass at 3 widths · PR → develop → master chain → prod verify.
