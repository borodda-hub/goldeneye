# Goldeneye — Innovation & Positioning Brief

*Code-grounded audit + strategic thesis. Internal. Written 2026-06-06.*
*Every claim below is cross-checked against the actual repo, not the pitch deck.
Honesty here is deliberate: a hungry, quant-literate firm will find the seams in
diligence — we lead with them so the real moat lands as credible.*

---

## 0. The one line

**The world is drowning in tools that claim to predict the market. Almost none
measure whether the analyst was actually *right for the right reasons*. Goldeneye
is a decision-intelligence terminal: it makes the human-plus-AI forecasting loop
*measurably* better — and proves it with receipts.**

Bloomberg measures the market. Goldeneye measures the analyst.

---

## 1. What we've actually built (honest inventory)

| Layer | Real & defensible | Thin / placeholder (diligence will find these) |
|---|---|---|
| **Backtest engine** | Genuinely look-ahead-safe: 3-layer defense (SQL cutoff, runtime assertion, property tests) + a *cheating-model proof* test that fails if future data leaks. This is hard and done right. | Single front-month contract (no rollover); early-window gaps. Prod `price_bars` are **seeded GBM**, not real history — no vendor backfill wired. |
| **Forecast ensemble** | 3 real models (MA cross, volatility-regime, Prophet). Dynamic confidence-weighted voting, honest input-diversity flag. | The "4th model" (XGBoost) is a **hardcoded heuristic, not trained ML**. Hit-rate uses a ±0.3% deadband that can flatter the numbers. |
| **AI / LLM layer** | 7 wired Claude features (market summary, signal explain, scenario narrate, journal review, thesis gen, thesis critique, DQ coach). Real per-task model routing (Haiku→Sonnet→Opus escalation), persona prompt-caching (~90% token savings), graceful degradation. | **Single-shot only** — no tool use, no RAG, no agentic loop. Confidence bands are **hardcoded "medium"**, not derived from model agreement. Default `LLM_MODE=fake`. |
| **Decision-quality engine** | The crown jewel. Captures **conviction-at-decision-time** (snapshot), then on resolution plots a real reliability diagram with sample-size guardrails. Per-bucket LLM coaching over *your* entries. **Auto-resolution from real market data is built** (`services/auto_resolution.py` + `POST /v1/journal/auto-resolve`, tested). Genuinely rare. | Cold-start (weeks before a bucket fills). Auto-resolution exists but is **not yet scheduled** — so resolution is manual *in practice* until a driver runs it. Evidence-weight captured but unused. Thesis backlink stored but not analyzed. |
| **Data** | Real official-source adapters live in prod across **5 domains** — EIA (storage/petroleum), CFTC (COT positioning), NWS (weather), Yahoo (delayed prices), RSS (news). 6 commodities (NG/CL/HO/RB/GC/SI), no vendor lock-in, all free/public APIs. | "Real-time" is a stretch: prices 15-min delayed, fundamentals weekly. Adapters are read-through + in-memory cache — **not persisted** to the Timescale hypertables (which exist, correctly configured, but unfed in prod). No tick/order-book data. |
| **Frontend** | Credible terminal: 8 full screens, ~149 components, 9 themes, deep chart stack (6 chart types, 15+ indicators, auto-S/R + trendlines, candlestick patterns, seasonality, drawing tools), WebSocket live updates, onboarding. No dead links, no "coming soon." | Scenario/paper forms are plain inputs; admin is static tables. Minor polish gaps, not structural. |

**Net:** the *scaffolding is real and unusually rigorous* (the backtest honesty and
the calibration engine are things most "AI trading" startups fake). The *predictive
alpha is not there yet* — and that's fine, because **alpha is the wrong thing to sell.**

---

## 2. The real moat (what's genuinely hard to copy)

1. **Decision-quality data that compounds.** Every analyst's calibration record —
   conviction-at-write vs. realized outcome, bucketed and scored — is proprietary,
   grows with use, and is *worthless to a competitor without the user's own history.*
   This is the classic data-moat shape, and almost nobody is building it for
   discretionary analysts.
2. **Epistemic honesty as architecture.** Forbidden-phrase enforcement, uncertainty
   wrapping, "research not advice," a backtest that *proves* it doesn't cheat. In a
   market where every AI tool over-promises and gets caught, *the system that is
   structurally unable to lie* is a trust product. That's a wedge with risk-conscious
   capital.
3. **The full loop already exists.** Thesis → evidence → conviction → scenario →
   backtest → outcome → calibration → coaching is wired end-to-end. Competitors have
   pieces; the integrated decision loop is the asset.

---

## 3. The reposition: stop selling prediction, sell *decision intelligence*

Predicting commodity prices is a commoditized, losing game to *promise*. But
**"we make your analysts measurably better forecasters, and we can prove who's
skilled vs. lucky"** is an uncontested, defensible, data-moated game. For a young
fund, this is the franchise:

- It solves a *real* unsolved problem — **talent evaluation & decision discipline.**
  Funds genuinely cannot tell skill from luck over short horizons. We can.
- It's honest — it doesn't require beating the market, so it survives diligence.
- It compounds — the calibration ledger is worth more every month.

---

## 4. The X-factors (innovation bets, each grounded in something real)

> Ordered by leverage. Each says: the bet, why it's defensible, what real thing it
> extends, and rough lift.

### X1 — The Calibration Flywheel ("a Brier score for your desk") ★ lead bet
Turn the decision-quality engine into the core product. **Auto-resolve** entries from
market data (kills the manual-resolution gap), give every analyst a live calibration /
Brier score, desk leaderboards, and **alpha-attribution: skill vs. luck.**
- *Defensible:* the calibration ledger is the data moat; switching cost rises monthly.
- *Extends:* the already-real conviction-at-write + reliability engine.
- *Lift:* low-medium. **The auto-resolution engine already exists** (`auto_resolution.py`)
  — the remaining lift is *scheduling* it + the live Brier scoring + a leaderboard view.
  The hard part (the conviction snapshot) is done.

### X2 — Agentic research copilot (the concierge, elevated)
Replace single-shot LLM with a **tool-using agent** that can actually query the data,
run a scenario, run a backtest, and draft a thesis with supporting/contradicting
evidence auto-populated — then red-team it. The "admin chatbot" idea, but wired to the
proprietary backtest + calibration substrate, not a chat wrapper.
- *Defensible:* the tools (backtest, calibration, scenario) are ours; a generic GPT
  wrapper can't reach them.
- *Extends:* the 7 existing LLM features + the routing/safety layer.
- *Lift:* medium-high. Tool-use plumbing over existing endpoints.

### X3 — The Devil's Advocate (adversarial thesis engine)
Make `critique_thesis` the signature feature: every thesis gets an automated
bull/bear debate, a pre-mortem, and "what would change your mind — here's the data to
watch." Sell the *discipline*: funds blow up from unchallenged conviction. This is a
**risk-management** story, not a prediction story.
- *Defensible:* tied to the live evidence + scenario substrate; framed as institutional
  process, not a toy.
- *Extends:* the already-real thesis critique + scenario lab.
- *Lift:* low-medium. Mostly orchestration + UX around an existing call.

### X4 — Calibrated ensemble ("models that know what they don't know")
Fix the hardcoded-confidence gap: derive confidence from **real model agreement +
each model's historical hit-rate by volatility regime**, then weight the ensemble by
*proven* calibration in the current regime. Turns honest-uncertainty architecture into
actual edge (e.g. calibrated position sizing).
- *Defensible:* requires the backtest history + regime classifier we already have.
- *Extends:* the real ensemble + look-ahead-safe backtest.
- *Lift:* medium. Replace one real model first (the XGBoost heuristic) with a genuinely
  trained model to retire the biggest credibility risk.

### X5 — The Decision Ledger (enterprise / compliance layer)
Every decision logged immutably with the evidence visible *at the time*. For a fund:
audit trail, regulatory defensibility, and structured post-mortems ("at the moment of
decision, here is exactly what you knew"). The conviction-at-write snapshot already
does the hard part.
- *Defensible:* B2B revenue + lock-in; compliance is sticky.
- *Extends:* the journal + snapshot machinery.
- *Lift:* medium. Immutability + post-mortem views.

### X6 — Calibrated-consensus meta-signal (the big swing)
Once many analysts are calibrated, the **calibration-weighted consensus** of the desk
becomes a proprietary in-house alpha source — each vote weighted by that analyst's
proven skill *in this regime*. No data vendor can sell this; it's made of your own
people's metacognition.
- *Defensible:* purest form of the data moat; literally uncopyable.
- *Extends:* X1 + X4.
- *Lift:* high; needs scale first. This is the year-2 vision slide, not the MVP.

---

## 5. Sequencing for a pitch

1. **Retire the worst credibility risk first** — replace the XGBoost heuristic with one
   genuinely trained model, and derive confidence honestly (X4 seed). Cheap insurance
   against a sharp DD question.
2. **Ship X1 (auto-resolution + desk calibration score)** — this is the demo that makes
   the repositioning real and shows the data moat.
3. **Ship X3 (Devil's Advocate)** — highest wow-per-effort; the risk-discipline story.
4. **Then X2 (agentic copilot)** as the "where this goes" narrative.
5. **X5 / X6** as the enterprise + year-2 moat slides.

The arc: *"We didn't build another oracle. We built the instrument that tells you which
of your people — and which of your models — actually deserve your capital, and we have
the receipts. Here's how that becomes an un-copyable edge as you scale."*

---

## Appendix — Portable "upstairs" prompt (paste into the Claude app)

> Use this for the wide blue-sky / GTM / narrative work. It carries the *real* facts so
> the model won't invent capabilities we don't have.

```
You are a strategy partner helping me sharpen the pitch for "Goldeneye," a natural-gas
/ commodity research + paper-trading terminal I want to sell to a young, ambitious
capital firm. Be ambitious but ruthlessly honest — assume the firm's diligence is sharp
and quant-literate. Do not invent capabilities beyond what I list.

WHAT IT REALLY IS (verified against the codebase):
- A research/paper-trading terminal (NOT a broker, NOT financial advice). Next.js +
  FastAPI + Postgres/TimescaleDB. 8 polished screens, deep charting, 9 themes, live
  WebSocket updates.
- REAL & rigorous: (a) a look-ahead-safe backtest engine with a "cheating-model" proof;
  (b) a decision-quality engine that snapshots an analyst's CONVICTION AT DECISION TIME
  and later plots a reliability diagram of conviction vs. realized outcome, with
  per-bucket LLM coaching — i.e. it measures decision quality separate from outcome luck;
  (c) live official-source data across 5 domains (EIA storage/petroleum, CFTC positioning,
  NWS weather, Yahoo delayed prices, RSS news) for 6 commodities, free/public APIs;
  (d) 7 wired Claude features with real per-task model routing + a safety layer that
  forbids advice/guarantee language.
- HONEST GAPS: the "4th forecast model" is a hardcoded heuristic, not trained ML; LLM
  confidence bands are currently hardcoded not derived; the LLM is single-shot (no tool
  use/agentic loop yet); prices are 15-min delayed and fundamentals weekly (not tick/
  real-time); production price history is currently seeded, not real backfill; calibration
  auto-resolution is built but not yet scheduled (manual in practice) and has a cold-start.

MY STRATEGIC THESIS: stop competing on price prediction (commoditized, can't promise) and
position as DECISION INTELLIGENCE — "Bloomberg measures the market; Goldeneye measures
the analyst." The moat is a compounding, proprietary calibration ledger (skill vs. luck)
plus epistemic-honesty-as-architecture.

WHAT I WANT FROM YOU — do this as a DEEP analysis, not a quick take:

1. PRESSURE-TEST THE WHOLE CONCEPT. Where is the "decision intelligence" repositioning
   weak? What would a skeptical, quant-literate partner attack in diligence? Is this the
   right wedge — or is there a stronger one hiding in the assets? If the angle is wrong,
   say so and propose a better one.
2. THE BUYER & THE MARKET. Name the strongest beachhead buyer (emerging fund talent-eval?
   decision discipline / risk? prop desk? RIA? in-house alpha?) and justify it. Roughly
   size the opportunity and the willingness to pay.
3. PITCH. Sharpen the 60-second and 5-minute narratives. Draft the competitive-positioning
   slide vs. Bloomberg / Koyfin / TrendSpider / generic "AI trading" tools.
4. NEXT-STEP FEATURE ROADMAP — this is the most important output. Give me a PRIORITIZED
   list of concrete, buildable features, grounded ONLY in the real assets above (no
   vaporware). For EACH feature provide, in this exact shape so I can hand it to my
   engineering copilot (Claude Code) and turn it into an implementation plan:
     - Name + one-line description
     - Why it's defensible (the one-sentence reason a copycat can't easily follow)
     - Which real asset it extends
     - Rough build effort: S / M / L
     - What it proves in a live demo
   Rank by leverage (impact per unit effort). Aim for 6–10 features spanning quick wins
   to the year-2 moat.
5. PRE-DILIGENCE FIXES. The 3 things I must build or fix BEFORE diligence so the honest
   gaps (heuristic "XGBoost", hardcoded confidence, seeded price history) don't sink it.

Be ambitious but ruthlessly honest. Push back on me. Do not invent capabilities beyond
the brief. End with a tight summary I can paste back to my engineering copilot to start
planning.
```
