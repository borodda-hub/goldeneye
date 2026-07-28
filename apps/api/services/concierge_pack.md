# Goldeneye Concierge Knowledge Pack

<!--
This file is the concierge's ONLY source of platform knowledge — it answers from
this pack, never from model priors. It is a curated distillation of:
  docs/MODEL_DILIGENCE.md (claims SOT), the /about white paper, docs/AI_BEHAVIOR.md,
  docs/ARCHITECTURE.md, and the screen inventory.
DRIFT-LOCK: tests/test_concierge_pack.py asserts the ANCHOR facts below stay
consistent with MODEL_DILIGENCE.md. If you change a claim here, change it there
(or vice versa) — the build fails otherwise, by design.
-->

## What Goldeneye is

Goldeneye is a research and paper-trading terminal for commodity markets (natural gas is
the showcase desk; crude, products, metals, an equity index, and rates run alongside).
It is NOT a broker, NOT a financial advisor, and executes no real trades — paper trading
is a self-contained simulator. It measures decisions, not just outcomes: users log
theses with stated conviction, the system resolves them against real prices, and a
calibration record shows how their claimed confidence compares to reality.

## The honest headline (never soften this)

- The platform's ONE validated predictive edge is the volatility/range engine: on ~10
  years of real daily prices across six commodities, walk-forward, the 80% price-range
  band covers 78-81% of outcomes and the 95% band covers 93-95%.
- DIRECTIONAL prediction has NO validated edge. Every directional model in the lineup
  was tested walk-forward on real data and none beat a drift-aware naive baseline.
  Feeding real CFTC positioning and EIA storage into the factor model made it worse,
  not better. Direction is shown as labeled VIEWS with attributed reasoning — never as
  probabilities, never as advice.
- Failed probes stay published on the Validation page (curve carry: failed;
  storage-surprise event edge: premise absent; vol-premium timing: promising on 2 of 3
  pairs, not crowned). Failures are results, not embarrassments.

## The screens (route → what it does)

- /dashboard — the working desk: price, directional bias (a VIEW, with supporting and
  contradicting factors), expected range band, fundamentals, positioning, news, AI
  thesis, paper-trading rail, watchlist.
- /chart — candlesticks with indicators (RSI, MACD, Bollinger and more), ~19
  candlestick patterns, auto-TA (support/resistance, trendlines), seasonality overlay.
  All descriptive/research-framed.
- /signals — Signal Lab: the four-model ensemble with per-model supporting and
  contradicting factors, model calibration records, backtest summaries, and the
  "Vol vs Market" card (our vol forecast vs the market's implied-vol index,
  descriptive only).
- /scenarios — Scenario Lab: apply shocks (weather, supply, storage...) to a baseline
  and see how the forecast shifts, with an AI narrative including the strongest
  counterargument. Includes a 3D impact globe for supply-chain scenarios.
- /journal — the Decision Journal: log a thesis (hypothesis, evidence, conviction,
  invalidation criteria); the system auto-resolves it against real prices later. The
  AI can critique the thesis and argue the other side (devil's advocate).
- /ledger — the append-only decision ledger: a hash-chained, tamper-evident record of
  what you knew at the moment of each decision.
- /paper — paper trading: simulated positions with real contract sizes, mark-to-market
  on real prices. No real money, ever.
- /calibration — the reliability diagram: your claimed conviction vs your realized hit
  rate, bucketed; the desk leaderboard with the skill-vs-luck verdict (a Wilson 95%
  confidence test that refuses to call streaks skill); DQ Coach patterns.
- /validation — the validation ledger: every claim with its data provenance and its
  tested verdict, including the failures. Drift-locked to the codebase.
- /admin — data/model health, environment, archive clocks (what evidence is
  accumulating toward future validation gates).
- /about — the white paper: methodology, architecture, and value in depth.

## How the forecasts work

Four transparent directional voters (moving average, Holt trend, factor composite,
walk-forward logistic regression) vote into an ensemble; confidence derives from
agreement, down-modulated by band width; chronically miscalibrated models are
down-weighted by their own record. A volatility-regime label (calm/normal/elevated/
crisis) stamps context. The range band comes from a separate, real-OOS-validated
engine (EWMA and log-HAR estimators; log-HAR is the default; empirical fat-tail
quantiles). Everything is look-ahead-safe: backtests reconstruct exactly what was
knowable on each historical date, and a deliberately cheating model must be caught by
CI, permanently.

## Data and freshness

Market prices are delayed real quotes; EIA storage and CFTC positioning are real
published data (weekly cadence); weather comes from NWS; news comes from per-symbol
multi-source RSS (EIA, Yahoo Finance, OilPrice, Kitco, NWS alerts) fetched live with a
~10-minute cache. Headlines can therefore be FRESHER than what the models have
ingested — when the concierge synthesizes from headlines, it labels that reasoning
"headline-derived — not yet in model inputs." Data provenance is observed, not
configured: the platform inspects what its database actually holds before claiming
anything is real.

## Rules the concierge must never break

- Never give personalized financial advice, position sizing, or buy/sell guidance of
  any kind. When asked "should I buy/sell/what will the price do", decline plainly and
  reframe: explain what the range band, the directional views, and the calibration
  tools actually offer, and that direction has no validated edge here.
- Never assert a specific future price level. Ranges with stated coverage are fine.
- Never use promissory language (the AI behavior contract's banned list).
- Never invent platform capabilities, numbers, or claims not in this pack or the live
  context provided with each question. If unsure, say so and point to /validation or
  /about.
- Mark inference as inference; label headline-derived synthesis explicitly.

## ANCHORS (drift-locked — keep byte-consistent with MODEL_DILIGENCE.md)

- ANCHOR:VOL80: 78-81% coverage
- ANCHOR:VOL95: 93-95% coverage
- ANCHOR:DIRECTION: no validated directional edge
- ANCHOR:FRESHNESS: headline-derived — not yet in model inputs
