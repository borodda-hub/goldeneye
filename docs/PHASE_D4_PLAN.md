# Phase D4 Plan — Storage-Day Event-Window Abstention (probe)

**Objective (MASTER_PLAN §4 D4):** weekly storage data is stale 4 of 5 days
— but on release day it is *news*. Test the sharp question only: conditional
on a LARGE EIA storage surprise (vs the 31a.0 consensus-free seasonal norm),
is the subsequent NG move predictable? If yes, the product ships an
**abstaining** view (silent most weeks, speaks only on extreme surprises,
carrying its own conditional calibration) — never an always-on signal.
Probe-first; no product surface until the gate passes.

**Status:** drafted + executed 2026-07-25 on `feat/phase-d4-storage-event`.

## Verified facts ([V])

- `eia_storage_reports` holds **730 real weekly rows (2012-07 → 2026-07)**,
  `report_date` = the publication Thursday (31a), `source='eia'`,
  `surprise_bcf` NULL (no consensus — the seasonal-norm proxy is the
  surprise measure, per 31a.0).
- `services/storage_features.delta_vs_seasonal_norm` is pure + walk-forward
  by construction (same-calendar-week 5y norm from prior rows only).
- NG=F continuous dailies fetch ~10y via the validators' production path;
  the probe requests a wider range (15y) to cover the feature span.
- Events are weekly and the primary horizon is ≤1w → **non-overlapping:
  n_eff = n** (the rare well-powered directional test).

## Design

- **Events:** every storage `report_date` (publication Thursday) with a
  computable walk-forward surprise (≥3 prior same-week years) and price
  bars around it. Surprise s = actual net change − 5y same-week norm
  (Bcf); positive = bigger build / smaller draw than normal ⇒ **bearish**
  hypothesis; negative ⇒ **bullish**.
- **Windows:**
  - *Reaction (sanity, G0):* release-day move = Wed close → Thu close.
    Not tradeable (the release lands intraday); measures whether the
    surprise moves price at all.
  - *Tradeable (the gate):* post-event drift, Thu close → next Thu close
    (1w). Entered strictly after the release is public.
- **Conditioning:** walk-forward expanding distribution of |s| (≥52-event
  warm-up); **extreme = outside the middle tercile**. The abstention claim
  is evaluated on extreme events ONLY (the view stays silent otherwise).
- Baselines: 0.50 chance AND the unconditional base rate of up-weeks AND
  drift-naive (trailing 100-day up-share) — the rule must beat the max.

## Pre-registered gates (locked before the first run)

- **P0 — power:** extreme-event count < 200 → INSUFFICIENT-N (expected
  ~400+, so this should not bind; it exists so a thin sample can't be
  crowned).
- **G0 — sanity (not a gate):** corr(s, release-day move) < 0 (surprise
  moves price the classic direction). If G0 fails, say so loudly — the
  premise itself is absent.
- **G1 — the abstention claim (primary):** on extreme events, the rule
  (s<0 ⇒ bullish, s>0 ⇒ bearish) hits the 1w post-event direction at a
  rate whose **~1 SE lower bound clears max(0.50, base-rate, drift-hit)**
  on the same events (n_eff = n; Wilson-consistent SE = √(p(1−p)/n)).
- **G2 — dose-response:** mean 1w post-event return monotone decreasing
  across walk-forward surprise quintiles, top−bottom ≥1 SE.
- **VERDICT:** PASS = G1 AND G2 → scope the abstaining view (own phase,
  S6-framed, conditional calibration readout). FAIL/PARTIAL → record;
  re-entry only via new data accumulating (gate unchanged).

## Change set

Probe only: `seeds/validate_d4_storage_event.py` (manual/network for
prices; features read from the DB). Docs in-commit: this plan, ledger row,
MASTER_PLAN D4 status, HANDOFF.

## Gates checklist (§7.4)

Health green · no schema/endpoint change (contracts untouched) · S3
untouched (read-only probe; surprise computed walk-forward) · S4 verdict
recorded either way · S7 docs in-commit · S8 two-lane promotion.

## D4 verdict (filled after the run)

See §verdict appended after execution.
