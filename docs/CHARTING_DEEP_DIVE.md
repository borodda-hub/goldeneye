# docs/CHARTING_DEEP_DIVE.md — Making the Chart Legit (futures-trader-grade)

_Deep dive: 2026-06-05. Goal: take the Chart page from a strong but **read-only,
un-styleable** analytical view to something a futures trader trusts on sight and
prefers to use — without losing the research/decision-support framing
(`CLAUDE.md`, `docs/AI_BEHAVIOR.md`). Complements `docs/CHARTING_ROADMAP.md`
(phases 20–25, which covered the analytical engine)._

## Honest assessment — where we stand

**What's genuinely good already** (don't rebuild): 6 chart types, 7 MAs + 8
oscillators/bands, a 12-EMA ribbon, 19 candlestick + 4 chart patterns, auto-TA
(S/R levels + trendlines), futures-curve overlay, multi-year seasonality, live
forming candle, per-symbol indicator persistence, screenshot/fullscreen, Redis-
cached indicator compute. The **math/analytics layer rivals mid-tier platforms.**

**Why it still reads "not legit" to a futures trader** — the chart is a *display*,
not an *instrument*:

1. **You can't draw on it.** No trendlines, rays, horizontal lines, Fibonacci,
   rectangles, or text. This is the #1 thing a discretionary futures trader does
   all day. Its absence is immediately disqualifying.
2. **You can't restyle it.** Dark-only, fixed candle colors, fixed grid, fixed
   crosshair, one font. Every serious platform opens with a settings gear that
   lets you own the look. (This is the user's explicit ask.)
3. **No right-click, no data window, no measure tool, no replay.** The standard
   interaction grammar traders have muscle-memory for is missing.
4. **No VWAP and no volume/market profile.** For *futures specifically*, these two
   are the "this person knows futures" tells.
5. **Timeframes stop at 1d** (no weekly/monthly), and there are no non-time bars
   (range/Renko/tick) or session/continuous-contract handling.
6. **One chart, one symbol.** No compare, no spread/ratio, no multi-pane layout.

The rest of this doc is the gap list, organized so the **cheap "look-legit" wins
come first**, then the big functional lifts, then the futures-pro tier, then our
research differentiators. Each item notes effort and whether the v5 primitives
API is required.

---

## Tier 0 — "Look legit" (cheap, high first-impression ROI)

These change perception more than capability. Most are LWC-v5 options we already
have access to — it's wiring + a settings UI + persistence. **Do these first.**

### 0.1 Chart Settings / Appearance panel ⭐ (the user's explicit ask)
A gear-icon panel (modal or right-rail) mirroring TradingView's "Settings" with
tabs. Persist everything to `localStorage goldeneye:chart:style:*`, and make it
**saveable as named "chart templates."** Controls to expose:

- **Symbol/candles:** up & down **body** color, **wick** color (independent),
  **border** color, **hollow up-candles** toggle, bar/line/area/baseline colors +
  width, price-source (close/hl2/hlc3) for line types, precision/tick rounding.
- **Background:** solid or **vertical gradient**, color picker.
- **Grid:** vertical/horizontal lines on/off, color, opacity (or "no grid").
- **Crosshair:** style (cross/dotted/solid), color, width, label background.
- **Scales/axis:** text color, font size, font family; scale on right/left/both;
  **last-price line + label** on/off; high/low price labels; **countdown to bar
  close**; indicator name/value labels in the legend.
- **Watermark:** symbol + timeframe ghost text (classic "legit" touch).
- **Theme presets:** Dark (current), Light, "Gold terminal" (brand), and
  user-saved. A light theme alone signals maturity.

Effort: ~3–5 days for the full panel + persistence + templates. **Highest
perception-per-effort item in the doc.** No v5 primitives needed — these are
`applyOptions()` calls on the chart/series.

### 0.2 Data Window (crosshair readout) ⭐
The floating/right-rail panel that shows **O H L C, change, %, volume, and every
active indicator's value at the crosshair's bar**. Traders rely on this constantly;
right now the chart shows only the implicit LWC tooltip. Subscribe to the
crosshair-move event and render a compact readout. Effort: ~1–2 days.

### 0.3 Right-click context menu ⭐
Standard grammar: *Add indicator… · Add alert at $X · Draw horizontal line here ·
Copy price/value · Reset price scale · Toggle log · Settings…*. Effort: ~1–2 days
(a positioned menu + the crosshair price under the cursor).

### 0.4 More timeframes + bar-close mechanics
- Add **weekly + monthly** (and `2h`/`4h` intraday). Aggregate daily→W/M on the
  backend or client. Futures research lives on weekly/monthly for structure.
- **"Scroll to realtime" / jump-to-latest** button when scrolled back.
- **Last-price line with countdown** to the bar close (0.1 covers the styling).

Effort: ~2 days.

### 0.5 Keyboard shortcuts + cursor modes
- Hotkeys: timeframe digits, `+`/`-` zoom, `Alt+drag` = measure, drawing-tool
  letters (T trendline, H hline, F fib…), `Esc` cancels a drawing, `Del` removes
  the selected object, `Ctrl+Z` undo last drawing.
- Cursor modes: **Cross / Dot / Arrow / Eraser**, and a **magnet** toggle
  (snap drawings to OHLC) — strong/weak.

Effort: ~2 days (pairs with drawing tools).

---

## Tier 1 — The functional credibility lift

### 1.1 Manual drawing tools ⭐⭐ (the single biggest gap) — needs v5 primitives
Implement `ISeriesPrimitive`-based drawables with select/move/edit/delete,
per-style options, magnet snapping, and **persistence per (symbol, timeframe)**
(localStorage now → DB later so they sync across devices). Minimum viable set, in
priority order:

1. **Horizontal line / ray** (price levels) — most-used, easiest primitive.
2. **Trendline** + **extended line / ray**.
3. **Fibonacci retracement** (then extension, fan, time zones).
4. **Rectangle / zone** (supply/demand boxes) + **ellipse**.
5. **Text / note / callout / arrow** (annotation).
6. **Measure tool** (drag to read Δprice, Δ%, Δtime, # bars) — also a Tier-0-ish
   quick win on its own.
7. **Parallel channel** + **Andrews pitchfork** (later).
8. **Long/short position tool** (entry/stop/target risk-reward box) — *frame as
   a research/journaling sketch, not order entry* (no broker; per AI_BEHAVIOR).

Supporting UI: a **left drawing toolbar** (the vertical icon strip traders expect)
and a **drawings/objects manager** (list, hide/lock/delete, jump-to). Effort:
~5–8 days for the first ~5 tools + toolbar + persistence; the rest incremental.
**This is what converts "chart widget" → "trading chart."**

### 1.2 Bar Replay / playback ⭐
Scrub the time axis back and step forward bar-by-bar (play/pause/speed). Enormous
for a *research* terminal — it's how you study setups and seed journal entries,
and it pairs perfectly with the decision-quality framing. Effort: ~3–4 days.

### 1.3 VWAP + Anchored VWAP ⭐ (futures table-stakes)
Session VWAP with ±σ bands, plus **anchored VWAP** (drop an anchor on any bar —
event, swing, session open). This is one of the two strongest "knows-futures"
signals. Backend indicator + an anchor interaction. Effort: ~2–3 days.

---

## Tier 2 — Futures-pro tier

### 2.1 Volume Profile / Market Profile (TPO) ⭐⭐ (the other futures tell)
- **Volume Profile**: visible-range, fixed-range (drag a window), and
  session-volume profiles, with **POC, Value Area (VAH/VAL)**. This is *the* most
  associated-with-futures study after VWAP.
- **Market Profile / TPO** (letters by time-price): the classic CME-pit-derived
  view; powerful and rarely done well — a real differentiator if we ship it.

Both need price-binned aggregation (backend) + a horizontal-histogram primitive
(frontend). Effort: ~4–6 days (volume profile first; TPO later).

### 2.2 Spreads, ratios & comparison (already roadmapped, leverage the 6 symbols)
- **Spread/ratio charts**: gold/silver ratio, crack spread (RB/HO vs CL),
  calendar spreads, CL/NG. Backend `services/spreads.py` aligns two series.
- **Compare / overlay** a second symbol, normalized to %, on the same pane.
- **Multi-pane layouts** (2×1, 2×2) with **synced crosshair + timeframe** (chart
  linking). Effort: ~4–6 days across the set; spread/ratio first.

### 2.3 Futures-specific data correctness
- **Session templates** (RTH vs ETH), session-break shading, custom session
  times, and a **session-aware time axis** (no flat weekend gaps on intraday).
- **Continuous contracts** with back-adjusted roll (so weekly/monthly history is
  contiguous across expiries) + roll markers. This is subtle but it's what
  separates a real futures chart from a stock chart. Effort: ~3–5 days.

### 2.4 Non-time bars
Range bars, **Renko**, tick bars, volume bars (Heikin-Ashi already done). Renko +
range especially are futures-trader favorites. Needs backend bar construction +
a time-axis that isn't strictly time. Effort: ~3–5 days.

### 2.5 Alerts on chart
Drag a line to set a **price alert**; indicator-cross and drawing-touch alerts;
an alert manager. Wires into the existing `alerts` table. Effort: ~3–4 days.

---

## Tier 3 — Differentiators (our edge over generic charts)

These are where we *beat* TradingView/TrendSpider for *this* audience, not match
them. They lean on assets we already have (LLM, backtest engine, seasonality,
decision-quality framework) and the research framing.

- **"Explain this chart" (live Claude)** — we now have real Claude wired. A button
  that narrates what's currently on screen (price structure, the active
  indicators, detected patterns, S/R) in the desk-analyst voice, caveated, with
  the safety envelope. *No other charting tool does AI narration of your exact
  view.* Effort: ~2–3 days (we have the LLM layer + pattern/auto-TA JSON to feed
  it). **Strong, cheap differentiator.**
- **Pattern-credibility backtest** (roadmapped) — "how reliably has *this* pattern
  resolved for *this* instrument?" hit-rate + decision-quality grade next to each
  detection. Reuses the Phase-10 backtest engine. The framing competitors lack.
- **More chart patterns + auto-Fib** — triangles (asc/desc/sym), wedges, flags,
  channels, **harmonic** (XABCD/Gartley/Bat/Butterfly), and auto-Fibonacci from
  detected swings. Extends the existing `chart_patterns.py`.
- **Pattern outlines as filled shapes** (not polylines) + **S/R heatmap zones**
  (TrendSpider-style) once primitives land.
- **Decision-journal hooks from the chart** — right-click a pattern/drawing →
  "seed a journal hypothesis" (ties charting into the existing journal/calibration
  loop; this is the product's actual moat).

---

## Suggested sequencing

1. **Tier 0 bundle** (settings/appearance panel + data window + right-click +
   weekly/monthly + scroll-to-realtime). Biggest perception jump per day; mostly
   `applyOptions()` + UI. Ship as one "Chart polish" phase.
2. **Drawing tools v1** (hline/ray, trendline, fib, rect, text, measure) + the
   left toolbar + persistence. The credibility unlock.
3. **VWAP/anchored VWAP**, then **bar replay**.
4. **Volume Profile** (+ POC/VA), then **spread/ratio + compare**.
5. **Session/continuous-contract correctness**, **alerts-on-chart**, **non-time
   bars**.
6. **Differentiators:** "Explain this chart" (cheap, do it early as a wow-factor),
   pattern-credibility backtest, harmonic/triangle patterns, S/R heatmap zones.

## Product-framing guardrails (unchanged)
- Drawing/position tools are **research sketches + journaling**, never order entry
  (no broker; per `CLAUDE.md`). The long/short tool computes risk-reward for study,
  not execution.
- Pattern/auto-TA/AI narration stays **descriptive**, carries the safety envelope,
  and never uses `§forbidden_phrases`. Reliability is shown via backtest/decision-
  quality, not implied by a drawn line.
- Customization is per-user and local-first (localStorage), DB-synced later.

## What we deliberately DON'T chase (execution-tier, off-mission)
Live DOM/ladder, order entry, broker integration, Level-2/footprint *execution*
tooling, and real-time tick-by-tick order flow. These belong to a live-execution
platform; we're a research + paper-trading terminal. (Cumulative delta / footprint
*as study tools* could come much later if tick data exists, but they're not the
priority.)
