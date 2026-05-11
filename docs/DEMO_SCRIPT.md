# docs/DEMO_SCRIPT.md — 5-Minute Demo Walkthrough

For an investor, collaborator, or new team member. Total runtime: ~5 minutes.

Prerequisite: `make demo` is running, UI is up at `http://localhost:3000`.

## Setup — 30 seconds

Open the UI. The left sidebar has seven items: Dashboard, Chart, Signal Lab, Scenario Lab, Decision Journal, Paper Trading, Admin. The footer carries the standard disclaimer — point at it briefly. ("This is a research and decision-support prototype. It does not provide personalized financial advice…")

The aesthetic: hairlines, no shadows, mono numbers. Bloomberg / Palantir / TradingView mindset. Color is reserved for signal — green for up, red for down, no decorative color.

## 1. Dashboard — 45 seconds

`/dashboard`

- Top: front-month NG price + intraday change + volatility regime chip (compressed / normal / elevated / crisis).
- Big chart with a 30-day mini-history overlay.
- Right rail: directional bias card (bullish / bearish / neutral with confidence band).
- Bottom row: futures curve and recent events (storage prints, weather flags, geopolitical).
- Bottom bar: live tick indicator — a green dot pulses as WebSocket ticks arrive on `price.NG.front`.

**Talking point:** "Single-screen, no scroll. Everything an analyst checks first thing in the morning."

## 2. Chart View — 45 seconds

`/chart`

- Full-viewport candlestick chart, Lightweight Charts under the hood.
- Resolution toggle (1m / 1h / 1d), SMA-20 and EMA-50 overlays.
- Event markers on the timeline — click one to open the event drawer with the parsed details (category, sentiment, impact score).

**Talking point:** "Same chart you'd see on TradingView, but the events come from our LLM-parsed news pipeline, not user clicks."

## 3. Signal Lab — 60 seconds

`/signals`

- **Ensemble header:** direction + confidence + vol regime + agreement count ("3 bull · 0 bear · 1 neutral of 4 · diversity: high"). Below: the confidence rationale — three short bullets that explain *why* the band is what it is.
- **Model grid:** 4 cards, one per model (moving average, prophet, volatility regime, gradient-boost placeholder). Each card shows direction, confidence, expected %, **inputs_used** tags (`closes` / `latest_storage` / `latest_cot`), top supporting factor (green border-left), top contradicting factor (red border-left).
- **Explanation panel:** LLM prose explaining the ensemble. Reads as institutional desk note — *appears*, *suggests*, *reads as*. Includes the SafetyEnvelopeNote (open by default) showing caveats and the disclaimer.
- **History table:** server-side hit/miss scoring with a ±0.3% deadband. Glyphs: ▲ hit, ▼ miss, ◇ indeterminate, — neutral (model called flat), ··· pending.

**Talking point:** "The 'agreement' fraction is the trust signal. When all 4 models agree and at least one uses non-price data, the ensemble actually says something. When they disagree, the tie-break is *neutral* — we never inherit direction from a one-tick momentum signal."

## 4. Scenario Lab — 60 seconds

`/scenarios`

- **Templates:** 6 preset cards. Click "Cold Snap — Northeast 10 Days."
- The shock builder populates with two weather shocks: `-12°F northeast for 10 days` and `-6°F midwest for 7 days`. Bounds are strict (Pydantic v2 discriminated union).
- Click **Run Scenario**.
- Result panel: directional pressure chip + confidence + timeframe + expected range, then three columns:
  - **Assumptions** — deterministic from shock metadata.
  - **Counterarguments** — deterministic, derived from shock types.
  - **Data needed to validate** — deterministic (NWS maps, EIA weekly storage, etc.).
- Below: LLM narrative prose in 5 sections (what the scenario assumes, how the data would shift, directional pressure with timeframe, strongest counterargument, validating signals).

**Talking point:** "The structural fields are deterministic — we don't let the LLM hallucinate counterarguments. The narrative is the only thing the model generates, and it's run through the same safety wrapper as everything else."

## 5. Journal → Paper Trade flow — 90 seconds

`/journal`

- Right side has the new-entry form. Fill in:
  - Hypothesis: "Cold snap rally setup — 3-5% over 2 weeks"
  - Evidence: add one row, source "NWS 6-10d", summary "Strong negative HDD anomaly Northeast"
  - Confidence: drag the slider to 65
  - Planned action: "Paper-long 2 NGF26 if storage delta < -10 Bcf"
  - Risk factors: "Above-normal storage, crowded long positioning"
  - Invalidation: "Front-month closes below 3.20 within 5 days"
- Submit. The entry appears in the list with a confidence bar.
- Click the new entry. The detail drawer opens with the LLM **review** — 4-6 bullets in assumption-finding mode. No directional language. No "this is a good trade." Bullets surface implicit assumptions, suggest evidence weight checks, identify missing risks.

`/paper`

- New-trade form right side. Fill in:
  - Contract: NGF26
  - Side: long
  - Size: 2 contracts
  - Entry: current mid (auto-fills from the dashboard)
  - Stop: 3.20, Take: 3.65
  - Journal ref: select the entry you just created
- Submit. The row appears in **Open Positions** with live mark-to-market PnL ticking via the price.NG.front WebSocket.
- Hit **Close**. The row moves to **Closed Trades** with the final PnL.
- Above the tables, **Equity Curve** updates — a Recharts line showing daily equity since the simulation started, $100k reference line, color shifts green/red based on current equity vs starting.

**Talking point:** "Journaling and paper trading are linked. The journal forces you to write down the *assumption-finding* questions before you put on the trade. The LLM review surfaces what you didn't write down. Then the paper trade locks in the decision — and the closed-trades table tells you, weeks later, whether the assumption held."

## Close — 30 seconds

Open `/admin` to show that everything's monitored — adapter cadences, model sample counts, recent alerts. Note that none of this is a real broker, none of it claims certainty, every screen carries the disclaimer in the footer.

The full pipeline runs locally, mock-first, with `LLM_MODE=fake` as the default. Real LLM and real adapters are drop-in replacements — see `docs/ROADMAP.md`.

End.
