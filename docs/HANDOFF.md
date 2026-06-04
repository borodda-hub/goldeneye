# docs/HANDOFF.md — Session handoff & next-steps plan

_Last updated: 2026-06-04. Read this first to pick up where we left off._

## TL;DR

Charting got a major overhaul (Phases 20–25), the dashboard gained two data
cards + a one-screen-fit pass, the thin-tier instruments (HO/RB/GC/SI) got real
backend data, and the long-broken `pnpm health` gate is **green end-to-end**.
754 backend tests, ~330 web tests, all gates passing. Clean working tree at
commit `285034f`. The charts page is now a multi-pane, pattern-aware, auto-TA,
seasonal commodity terminal.

---

## What shipped this session (15 commits, `d805cca` → `285034f`)

### Arc 1 — Soundness: restore the health gate
The session opened on a broken `pnpm health`. Root-caused and fixed in order:
- **`d805cca`** — mypy gate restored. The real cause was `db/engine.py` alone
  importing `from src.settings` while 13 other modules use
  `apps.api.src.settings`; that second module name made `mypy --strict` fail
  ("Source file found twice"). Consolidating to the canonical path fixed it (no
  pandas-stubs flood appeared). Note: `[tool.mypy] files=["src"]` only strict-
  checks `main.py`+`settings.py` — a narrow pre-existing scope.
- **`5cd3d60` / `97ca0d7` / `b70d3fb`** — biome cleared **200 → 0**: 147 cosmetic
  autofixes, 7 zero-risk fixes, then the final 43 a11y/array-key/hook-dep
  findings (documented `biome-ignore` on static lists + custom-styled controls,
  structural button-wrap for sortable table headers, Escape onKeyDown on modal
  backdrops). `pnpm health` has been green ever since.

### Arc 2 — Thin-tier data + dashboard usability
- **Phase 17 (`a54c5d0`)** — backend data-correctness for HO/RB/GC/SI:
  `EIAPetroleumAdapter(symbol)` + `PETROLEUM_SERIES` (CL/HO/RB), CFTC `MARKETS`
  + `instruments.json cftc_market_code`, per-symbol `cot_generator` (NG byte-
  identical), curated news configs + `monetary` category, `NullEnergyAdapter` +
  `get_energy()` routing. Live-verified CFTC codes + EIA series.
- **Phase 18 (`4209957`)** — **Fundamentals** + **Positioning** dashboard cards
  with dedicated endpoints (`/v1/fundamentals`, `/v1/positioning`). Verified
  per-symbol (gas storage / petroleum stocks / honest metals empty state; COT
  managed-money net).
- **Phase 19 (`8e57d04`/`ad9543d`/`ac9e080`)** — dashboard one-screen fit:
  thesis cards default collapsed (the AI Thesis card was 660px — the dominant
  consumer), card row sized to content, chart/curve rows trimmed. Content went
  1854px → ~950–1140px.

### Arc 3 — Charting overhaul (the bulk of the session)
Full plan + per-phase closeouts in **`docs/CHARTING_ROADMAP.md`**.
- **Phase 20 (`2e5918a`)** — quick wins: chart-type toggle (candlestick/bars/
  Heikin-Ashi/line/area/baseline), live forming candle, log scale, range presets
  + resolution persistence, futures-curve overlay, PNG export + fullscreen.
- **Phase 21 (`3d0dd15`)** — candlestick pattern recognition: ~19 hand-coded
  patterns (`services/patterns/candlestick.py`), `GET /v1/chart/patterns`,
  direction-colored markers. Descriptive/research-framed (safety envelope).
- **Phase 22 (`56b1ae1`)** — **Lightweight Charts v4 → v5 migration** (the gate
  for panes + primitives). `addSeries(Def, opts)` + `createSeriesMarkers`.
- **Phase 23 (`b0ac7f6`)** — oscillators (RSI/MACD/Stochastic/ADX/ATR sub-panes)
  + bands (Bollinger/Keltner/Donchian). The indicator engine now returns
  `pane` + named `lines[]`.
- **Phase 24 (`cefa4d2`)** — auto-TA: support/resistance levels, trendlines,
  double top/bottom, head & shoulders. `GET /v1/chart/auto-ta`, **Auto-TA**
  toggle, overlays via v5 price-lines + line-series.
- **Phase 25 — seasonality core (`285034f`)** — **Season** toggle → per-year
  price overlay on a Jan→Dec axis + cross-year average. `GET /v1/chart/seasonality`.

---

## Current state

- **Tests:** backend **754** passing; web ~**330** (incl. chart tests). `pnpm
  health` GREEN end-to-end (ruff → mypy → pytest → web lint → typecheck → test).
- **Charts page** now has toolbar toggles: resolution · range · chart-type ·
  LOG · Curve · Patterns · Auto-TA · Season · Indicators (RSI/MACD/Bollinger/…
  presets) · PNG · fullscreen.
- **Dashboard** shows Fundamentals + Positioning cards; thesis cards collapsed
  by default; fits ~one screen on a large display.
- Working tree clean at `285034f` on `master`.

### Key architecture notes (for whoever picks this up)
- **Indicator engine** (`services/indicators/`): `compute()` returns
  `IndicatorSeries{type, params, pane, lines[]}`. MAs return a bare `pd.Series`
  (wrapped as one `"line"` on the `price` pane); oscillators/bands return an
  `IndicatorResult(pane, lines)`. Spec grammar: MAs `type:period[:source]`,
  others positional (`macd:12:26:9`, `bb:20:2`) via `_PARAM_SCHEMA` in
  `routers/indicators.py`.
- **Pattern services** (`services/patterns/`): `candlestick.py` (Phase 21),
  `chart_patterns.py` (Phase 24, auto-TA). Both pure-numpy, no scipy/TA dep,
  deterministic + unit-tested. Endpoints in `routers/patterns.py`
  (prefix `/v1/chart`, routes `/patterns` + `/auto-ta`, shared `_fetch_bars`).
- **Frontend chart** is Lightweight Charts **v5**. `PriceChart.tsx` holds the
  chart/series in refs (structural effect + separate live-tick effect);
  sub-pane indicators use `addSeries(def, opts, paneIndex)`; markers via
  `createSeriesMarkers`. `SeasonalityChart.tsx` is a separate v5 chart.
- Chart prefs persist in `localStorage` under `goldeneye:chart:*`.

### Operational gotchas (Windows dev)
- **uvicorn `--reload` (WatchFiles) intermittently stops detecting changes.**
  After adding new backend files, the running server often won't pick them up —
  restart the stack.
- **`TaskStop` on `pnpm dev` orphans the uvicorn worker children** (they hold
  port 8000 via an inherited socket). Clean restart: kill the
  multiprocessing-spawn `python.exe` workers + any listeners on 8000/3000/3001
  via `taskkill /F`, confirm ports free, then `pnpm dev`.
- **Re-seed** after a schema/seed change:
  `uv run --directory apps/api python -m seeds.demo --fresh`
  (use `-m seeds.demo`, NOT `-m apps.api.seeds.demo` — `apps` isn't importable
  from cwd `apps/api`; `seeds.demo` works because demo.py bootstraps repo-root).
- **Contract regen** (after a response-model change): with the dev server up,
  `curl -s http://localhost:8000/openapi.json -o packages/contracts/openapi.json
  && pnpm contracts:gen:local`.
- **Playwright** chromium is installed. Drive the chart headless with a temp
  `.mjs`; set `localStorage goldeneye:walkthrough-completed = "1"` in
  `addInitScript` to suppress the first-run tour overlay.

---

## Next-steps plan (start-fresh-ready)

### Track A — Finish Phase 25 (charting differentiators), in value order
1. **Spread / ratio charts** _(recommended next — strongest remaining gas-desk
   feature; leverages the 6 instruments)_.
   - Backend: `GET /v1/chart/spread?a=GC&b=SI&kind=ratio|spread` → align two
     instruments' daily closes by date, compute ratio (a/b) or spread (a−b) as a
     time series. New `services/spreads.py` + route in the chart router.
   - Frontend: a spread mode — a small two-symbol picker (A / B + ratio/spread
     toggle) and render the derived series as a line (reuse the line chart-type
     path, or a dedicated lightweight view). Presets: gold/silver ratio, CL/NG,
     crack spread (RB/CL or HO/CL).
   - Effort: ~½–1 day. Mostly backend align-and-compute + a small picker.
2. **Pattern-credibility backtest** _(the research-framing differentiator)_.
   - "How reliably has *this* pattern resolved for *this* instrument?" Reuse the
     Phase-10 backtest engine: for each detected candlestick/chart pattern, look
     forward N bars and measure hit-rate; surface a stat + the decision-quality
     grade next to the pattern. Ties pattern recognition into the existing
     decision-quality framework — nothing else on the market frames it this way.
   - Effort: ~1–2 days.
3. **Manual drawing tools** (trendline / horizontal-ray / Fibonacci / rectangle /
   text) via v5 **primitives**; persist per-symbol in `localStorage`.
   - Highest effort, most generic. v5 primitives require implementing
     `ISeriesPrimitive` + pointer interaction. Do this last in the track.
   - Effort: ~3–5 days (split per tool).
4. **Multi-symbol comparison overlay**, **alerts-on-chart** (ties into the
   existing `alerts` table), **harmonic patterns** (XABCD/Gartley), **triangles/
   wedges/flags** + **auto-Fibonacci** levels, **LLM narration** of detected
   patterns (the `description`/`meaning` strings are returned but could be
   LLM-elevated via `services/llm_explainer.py`).

### Track B — Small backlog (quick, independent)
- **Oscillator custom-param editing** — the IndicatorPicker form is MA-only;
  oscillators/bands are preset-only (default params). Make the form data-driven
  off `OSC_CATALOG.paramOrder` so MACD/Bollinger params are editable.
- **Candlestick `meaning` hover tooltip** — the per-detection `meaning` string is
  returned by `/v1/chart/patterns` but not surfaced; show it on marker hover or
  in the EventDrawer.
- **Phase-19 leftovers** — the first-run **walkthrough tour dims the dashboard**
  (auto-skip or lighten it); the **"MOCK" source label** on the Positioning card
  + NG fundamentals reads loud (it's honest demo-seed data — soften/relabel,
  since CL/HO/RB fundamentals are genuinely live EIA).

### Track C — Product directions still open (pre-charting backlog)
From the original menu (see memory `project_phase_state.md`):
- **Deploy to a shareable URL** (Vercel + Railway + Upstash; deploy prep already
  landed in `7d22cc2`).
- **LLM telemetry** (deferred from Phase 09).
- **Production observability (OTel)**.
- **Metals macro panel** (DXY / real yields / FOMC) to fill the GC/SI
  fundamentals empty state.
- **EIA petroleum history hypertable** (the petroleum adapter doesn't persist).
- **More asset classes** (the +20 commodities are in the watchlist but only
  NG/CL/HO/RB/GC/SI have the full data tier).

### Recommended first move next session
Pick up **Track A #1 (spread/ratio charts)** — it's the highest-value remaining
charting feature, leans into the multi-instrument work, and is a clean ~½-day
increment. Or, if shifting away from charts, **Track C deploy** to get a
shareable URL in front of people.

---

## Pointers
- `docs/CHARTING_ROADMAP.md` — the 6-phase charting plan + per-phase closeouts.
- `docs/PHASE_17_PLAN.md` — thin-tier plan + closeout.
- `~/.claude/.../memory/project_phase_state.md` — running phase state (most
  detailed; auto-loaded each session).
- Source-of-truth docs unchanged: `ARCHITECTURE.md`, `SCHEMA.md`,
  `API_CONTRACTS.md` (now documents the Phase-18/21 endpoints), `AI_BEHAVIOR.md`,
  `MOCK_DATA_SPEC.md`, `FRONTEND_COMPONENTS.md`, `DATA_SOURCES.md`.
