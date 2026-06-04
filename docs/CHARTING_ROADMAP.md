# docs/CHARTING_ROADMAP.md — Charting & Pattern-Recognition Roadmap

Phased plan to take the Chart page from a lean MA-overlay view to a
TradingView/TrendSpider-class research surface, **framed for a research and
decision-support terminal** (per `CLAUDE.md` and `docs/AI_BEHAVIOR.md`): pattern
recognition here is **descriptive and educational** — it annotates and explains,
it does not say "buy now." Every pattern/auto-TA output is surfaced with
uncertainty and feeds the decision-quality framework, never trade instructions.

## Current state (baseline, 2026-06-04)

Lightweight Charts **v4.2** · candlesticks + volume histogram · **7 moving
averages** (SMA/EMA/WMA/HMA/DEMA/TEMA/VWMA) + 12-EMA Ribbon preset · EIA event
markers · crosshair/zoom/pan · per-symbol indicator persistence · 5 resolutions
(1m–1d). **Overlay-only and read-only.** Files: `components/chart/PriceChart.tsx`,
`ChartToolbar.tsx`, `lib/chart/indicatorRegistry.ts`, `IndicatorPicker.tsx`,
`app/(app)/chart/ChartShell.tsx`; backend `services/indicators/` (MAs only),
`routers/indicators.py`, `routers/chart.py`.

## What industry-leading tools do (research)

| Tool | Pattern-recognition capability |
|---|---|
| **TradingView** (Premium "Auto Chart Patterns") | Auto-detects H&S/inverse, double & triple tops/bottoms, wedges, triangles (asc/desc/sym), rectangles, flags; scans last ~600 bars; auto candlestick patterns. |
| **TrendSpider** ("king of AI TA") | Auto trendlines, auto Fibonacci, support/resistance **heatmap zones**, **148 candlestick patterns**, chart patterns in real time, multi-timeframe overlay, point-and-click backtesting of detected setups. |
| **NinjaTrader** | Built-in Candlestick Pattern indicator + TrendLines indicator (auto trend/S-R); 3rd-party **harmonic** (XABCD/Gartley) recognition; Strategy Analyzer backtests pattern setups. |
| **TA-Lib / pandas-ta** | The math layer everyone builds on: 60+ candlestick patterns (`CDL*`), 150–200 indicators. |

The common feature set to target: **(a) candlestick patterns, (b) classic chart
patterns, (c) auto support/resistance + trendlines + Fibonacci, (d) harmonic
patterns, (e) backtest/credibility of detected patterns.**

## Architecture decisions

- **Charting lib:** migrate **Lightweight Charts v4 → v5**. v5 adds native
  **panes** (oscillators below price) and **primitives** (the foundation for
  drawing tools + pattern overlays). This single migration gates oscillators,
  drawing tools, and pattern-shape rendering — so it sits early in the plan.
- **Pattern/indicator math (backend):** use **`pandas-ta-classic`** — a
  pure-Python (numba/numpy) library with **192 indicators + 62 native candlestick
  patterns, no C dependency**. This avoids TA-Lib's C-build pain on the existing
  Python 3.12 stack (which already has pandas/numpy). Keep it behind a thin
  `services/patterns/` wrapper so it's swappable.
- **Chart-pattern detection (backend):** rule-based geometry on **`scipy.signal`
  peak detection** + a rolling-window of recent price extremes + validation
  rules (neckline, peak symmetry, slope convergence). This is the documented,
  deterministic approach (no ML needed for v1) and fits the mock-first ethos.
- **Framing:** all pattern output passes the existing safety layer
  (`services/safety.py`) and is narrated by `services/llm_explainer.py` in the
  desk-analyst voice (descriptive, caveated). Reliability is shown via the
  existing backtest + decision-quality machinery — **this is the differentiator
  vs. generic charting tools.**

---

## Phase 20 — Chart quick wins (no v5 needed) · ~1–2 days

High-visibility polish that LWC v4 already supports.
- **Live-updating bar** — the forming candle ticks in real time. Already wired
  (`ChartShell` subscribes to `price.{sym}.front.1m` but discards it —
  `void livebar`); just append/update the last bar.
- **Chart-type toggle** — candlestick / line / area / OHLC bars / Heikin-Ashi /
  baseline (LWC v4 series types). Toolbar segmented control + persistence.
- **Log/linear price-scale toggle**; **autoscale** button.
- **Resolution persistence** (localStorage, per-symbol) + add **weekly/monthly**;
  **date-range presets** (3M/6M/1Y/2Y/5Y/All) instead of the fixed 2-yr fetch.
- **Render the futures-curve overlay** — data is already fetched and passed to
  `PriceChart` (`initialCurve`) but never drawn; add term-structure
  (contango/backwardation) rendering.
- **Screenshot/export** (`chart.takeScreenshot()`) + **fullscreen**.
- Acceptance: each toggle persists; live bar updates; no regression in markers.

## Phase 21 — Candlestick pattern recognition · ~2–3 days (no v5 needed)

The highest-value pattern feature, and it's mostly backend math + marker render.
- Backend: add `pandas-ta-classic`; `services/patterns/candlestick.py` computes
  the CDL set on bars; `GET /v1/chart/patterns?symbol=&resolution=&from=&to=`
  returns detections `{ts, name, direction: bullish|bearish|neutral, strength}`.
- Each detection wrapped via `safety.py`; classification is descriptive only.
- Frontend: render pattern markers (reuse the event-marker mechanism in
  `PriceChart`), a **Patterns** toggle/legend in `ChartToolbar`, hover shows the
  pattern name + plain-English meaning (e.g. "Bullish engulfing — the up-candle
  fully covers the prior down-candle; *suggests* buyers stepped in").
- **Decision-journal hook:** a detected pattern can seed a journal hypothesis
  (ties into Phase 12/13 work) — research framing, not a signal to act on.
- Acceptance: 30+ patterns detect on seeded NG bars; markers + legend; safety
  envelope present; contract regen + tests.

## Phase 22 — Lightweight Charts v4 → v5 migration (enabler) · ~2–3 days

- Migrate `PriceChart.tsx` to v5 (panes + primitives API). Regression-test
  candles, volume, the 7 MAs, event markers, Phase-21 pattern markers, resize.
- No new user features — this unlocks Phases 23–24. Worktree-isolate; keep v4
  behind a flag until parity is verified.
- Acceptance: visual + test parity with the v4 chart; bundle size noted.

## Phase 23 — Oscillators + bands/channels in sub-panes · ~3–4 days (needs v5)

Completes the long-standing Phase 15/16/17 indicator follow-ups.
- Backend: extend `services/indicators/` (via pandas-ta-classic) with **RSI,
  MACD, Stochastic, ADX/DMI, ATR, OBV** (sub-pane) and **Bollinger, Keltner,
  Donchian** (overlay bands). Extend the `spec` grammar + `GetIndicatorsResponse`.
- Frontend: **sub-pane rendering** (v5 panes), a band renderer, categorized
  `IndicatorPicker` (Trend / Momentum / Volatility / Volume), per-pane scaling.
- Acceptance: each indicator renders in the correct pane; persists per-symbol;
  picker categories; tests.

## Phase 24 — Auto chart patterns + auto-TA (TrendSpider/TradingView tier) · ~4–5 days (needs v5 primitives)

- Backend `services/patterns/chart_patterns.py`: scipy-peak + rolling-extreme +
  geometric validation. Detect **support/resistance zones, auto-trendlines,
  auto-Fibonacci, head & shoulders (+inverse), double/triple tops & bottoms,
  triangles (asc/desc/sym), wedges, rectangles, flags, channels**. Each with a
  **confidence score** and the geometry (points/lines/zones).
- `GET /v1/chart/auto-ta?symbol=&resolution=` → detected geometries + confidence.
- Frontend (v5 primitives): draw trendlines, S/R **heatmap zones**, Fibonacci,
  and pattern outlines; a toggle panel to enable/disable each detector.
- **LLM narration:** `llm_explainer` describes each detected pattern in the
  desk-analyst voice with caveats ("a symmetrical triangle *appears* to be
  forming; *however*, volume has not confirmed…") — never a directive.
- Acceptance: detectors fire on seeded + live bars; overlays render; narration
  passes the forbidden-phrase scan; tests.

## Phase 25 — Differentiators: pattern credibility, drawing tools, seasonality, spreads · ~5–7 days (stretch, split as needed)

What makes it a **gas/commodity research terminal**, not a generic chart widget.
- **Pattern credibility / backtest** — reuse the Phase-10 backtest engine to
  answer "how reliably has *this* pattern resolved for *this* instrument?" and
  surface a hit-rate + the decision-quality grade. This is the research framing
  competitors don't have.
- **Manual drawing tools** (v5 primitives): trendline, horizontal/ray,
  Fibonacci, rectangle, text — persisted per-symbol.
- **Seasonality overlay** — same calendar window across N years (the core
  gas/energy view; Bloomberg-GIP equivalent).
- **Spread / ratio charts** — gold/silver ratio, crack spread, calendar spreads,
  CL/NG; you now have 6 instruments to spread.
- **Multi-symbol comparison overlay** + **price/pattern alerts on chart** (ties
  into the existing `alerts` table).
- **Harmonic patterns** (XABCD/Gartley/Bat/Butterfly) as a final stretch.

## Sequencing rationale

20 (quick wins, independent) → 21 (candlestick patterns, independent, high value)
→ **22 (v5 migration, the unlock)** → 23 (oscillators/bands) → 24 (auto chart
patterns) → 25 (differentiators). Phases 20–21 deliver visible value with zero
architectural risk; 22 is the gate; 23–25 are the pro tier. Each phase is
independently shippable and testable.

## Product-framing guardrails (apply to every phase)

- Descriptive, not prescriptive — patterns are *observations*, narrated with
  inference markers and caveats; no `§forbidden_phrases`.
- Every pattern/auto-TA output carries the safety envelope and the disclaimer.
- Reliability is shown via backtest/decision-quality, not implied by drawing a
  line on a chart.
- Mock-first: detectors run deterministically on seeded bars before any live use.

## Sources (research, 2026-06-04)

- TradingView — Auto Chart Patterns: https://www.tradingview.com/support/solutions/43000690464-auto-chart-patterns-on-tradingview/
- TrendSpider — Automated Chart Pattern Recognition: https://help.trendspider.com/kb/automated-technical-analysis/automated-chart-pattern-recognition
- NinjaTrader — Trade Chart Patterns / TrendLines indicator: https://ninjatrader.com/futures/blogs/chart-patterns-trading/
- TA-Lib: https://ta-lib.org/
- pandas-ta (and pandas-ta-classic, native CDL patterns): https://www.pandas-ta.dev/ · https://pypi.org/project/pandas-ta-classic/
- Algorithmic chart-pattern detection (scipy peaks + rules): https://alpaca.markets/learn/algorithmic-trading-chart-pattern-python · https://github.com/zeta-zetra/chart_patterns
