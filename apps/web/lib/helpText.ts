/**
 * Plain-language explanations for feature headers, surfaced via <HelpTip>.
 *
 * Tone rules (see docs/AI_BEHAVIOR.md): descriptive and research-framed. Never
 * advice, never a recommendation, never a certainty/return claim. These are
 * "what this panel shows", not "what you should do". Keep each to 1–2 short
 * sentences a first-time user can follow.
 */
export const HELP = {
  // ── Dashboard ──────────────────────────────────────────────
  aiThesis:
    "An AI-written summary of the current setup for this instrument — what the models and data are pointing at right now. A research narrative, not advice.",
  workingThesis:
    "Your own running notes on this instrument. Edit it to track your reasoning over time — it's just for you.",
  directionalBias:
    "The models' net lean for this instrument — up, down, or flat — with how strongly the ensemble agrees. Descriptive only, not a recommendation.",
  futuresCurve:
    "Prices for delivering this commodity in future months. An upward slope (contango) or downward one (backwardation) reflects market expectations about supply and demand.",
  recentEvents:
    "Latest news and scheduled events (like the weekly EIA storage report) relevant to this instrument.",
  fundamentals:
    "Supply-and-demand data for this instrument — e.g. EIA weekly inventory versus the 5-year average. Metals aren't covered by EIA inventory reports.",
  positioning:
    "How 'managed money' (hedge funds and similar) are positioned in the weekly CFTC report: long contracts minus short. A crowded position can hint at sentiment.",
  paperEquity:
    "Your simulated account value from paper (practice) trades. No real money is involved.",
  priceMini:
    "Recent price history for this instrument over the window you pick above.",
  openPositions: "Your currently open paper (practice) trades.",
  recentTrades:
    "Paper trades you've recently closed, with their simulated P&L.",
  signalQuality:
    "A quick read on how trustworthy today's signal looks, based on model agreement and recent accuracy.",

  // ── Signal Lab ─────────────────────────────────────────────
  ensemble:
    "The combined view across all forecast models: net direction, confidence, and how much the models agree with each other.",
  models:
    "Each forecasting method's own read — e.g. a moving-average cross, a trend model, a volatility-regime model. They often disagree; that's expected.",
  backtest:
    "How each model would have scored against real past prices — its historical hit rate. Past performance doesn't predict future results.",
  explanation:
    "A plain-language, AI-generated walk-through of why the signal looks the way it does. A research narrative, not advice.",
  signalHistory:
    "Past forecasts for this instrument and how they resolved against the actual prices that followed.",

  // ── Scenario Lab ───────────────────────────────────────────
  scenarioLab:
    "A 'what if' sandbox: pose a situation (a cold snap, a storage surprise) and see how the models think prices might respond. Research only — no real trades.",
  templates:
    "Pre-built scenarios you can load as a starting point, then tweak.",
  shockBuilder:
    "Define the shocks that make up your scenario — e.g. a temperature drop in a region, or a storage surprise — then run it.",
  scenarioResult:
    "The model's read on your scenario: likely direction, confidence, an expected range, plus its assumptions and what could prove it wrong.",
  assumptions:
    "The conditions the model is taking as given for this scenario. If these don't hold, the result changes.",
  counterarguments:
    "Reasons the scenario could play out differently — the case against this read.",
  dataNeeded:
    "What you'd want to check in the real world to confirm or reject this scenario.",
  recentRuns: "Scenarios you've run recently — select one to revisit it.",

  // ── Chart toolbar ──────────────────────────────────────────
  resolution: "How much time each candle represents, from 1 minute to 1 day.",
  dateRange: "How far back in history the chart loads.",
  chartType:
    "Switch between candlestick, bars, Heikin-Ashi, line, area, or baseline views.",
  logScale:
    "Logarithmic price scale — equal percentage moves take equal vertical space. Handy across large price ranges.",
  curveOverlay:
    "Overlay the futures curve (prices of later-month contracts) on the chart.",
  patterns:
    "Marks classic candlestick patterns (doji, engulfing, hammer…). Descriptive labels for study — not buy or sell signals.",
  autoTa:
    "Auto-draws support/resistance levels, trendlines, and shapes like double-tops. A research aid, not advice.",
  seasonality:
    "Overlays each year's price on a shared Jan–Dec axis so you can compare seasonal patterns.",
  indicators:
    "Add studies like moving averages, RSI, MACD, or Bollinger Bands to the chart.",
} as const;

export type HelpKey = keyof typeof HELP;
