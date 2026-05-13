/**
 * Walkthrough step definitions.  Each step targets a DOM element via CSS
 * selector (preferred: `data-testid` or `data-tour` attributes).  When
 * `targetSelector` is null the step renders as a centered modal — used for
 * the welcome and farewell screens.
 *
 * When `routeRequired` is set and differs from the current pathname, the
 * provider pushes the router before the step renders.  The overlay polls
 * for the target so the new page has time to mount.
 */
export type StepSide = "top" | "bottom" | "left" | "right" | "center";

export interface WalkthroughStep {
  id: string;
  /** CSS selector for the target.  null → centered modal. */
  targetSelector: string | null;
  title: string;
  body: string;
  /** Where to place the tooltip relative to the target.  Ignored for center. */
  side: StepSide;
  /** Optional URL the provider should navigate to before this step. */
  routeRequired?: string;
}

export const DASHBOARD_TOUR: WalkthroughStep[] = [
  // ── Welcome ────────────────────────────────────────────────────
  {
    id: "welcome",
    targetSelector: null,
    title: "Welcome to Goldeneye",
    body:
      "A guided walkthrough of the terminal — about fourteen stops across every screen. Esc dismisses, arrows step. You can re-launch this any time from the top bar.",
    side: "center",
    routeRequired: "/dashboard",
  },

  // ── Dashboard ──────────────────────────────────────────────────
  {
    id: "watchlist",
    targetSelector: '[aria-label="Watchlist"]',
    title: "Watchlist",
    body:
      "Switch instruments. Every page — Signal Lab, Scenarios, Journal, Paper Trading, Calibration — refetches against your pick. URL and localStorage preserve the selection across reloads and tabs.",
    side: "right",
    routeRequired: "/dashboard",
  },
  {
    id: "working-thesis",
    targetSelector: '[data-tour="working-thesis"]',
    title: "Working Thesis",
    body:
      "Your current view as a first-class object. Supporting + contradicting evidence auto-populate from the latest ensemble forecast and scenario run. Your conviction percentage feeds the calibration loop.",
    side: "bottom",
    routeRequired: "/dashboard",
  },
  {
    id: "signal-quality",
    targetSelector: '[data-testid="signal-quality-chip"]',
    title: "Signal Quality grade",
    body:
      "Composite of input diversity, model agreement, regime stability, and data freshness. Click the chip for the per-sub-score breakdown.",
    side: "bottom",
    routeRequired: "/dashboard",
  },
  {
    id: "resize",
    targetSelector: '[data-testid="resizable-split-handle"]',
    title: "Resize the panes",
    body:
      "Drag this hairline to rebalance the chart and the directional bias card. Width persists per-user. Keyboard: focus + ← / → nudges in 16-px steps.",
    side: "right",
    routeRequired: "/dashboard",
  },
  {
    id: "ticker",
    targetSelector: '[data-testid="dashboard-ticker"]',
    title: "Macro context",
    body:
      "Indices, commodities, and macro pairs scrolling at the foot. Hover to pause. Yahoo-delayed quotes refreshed every five minutes.",
    side: "top",
    routeRequired: "/dashboard",
  },
  {
    id: "side-nav",
    targetSelector: 'nav[class*="border-r"]',
    title: "Six more screens",
    body:
      "The rest of the terminal — Chart, Signal Lab, Scenario Lab, Journal, Paper Trading, Calibration, Admin. We'll visit the headline feature on each.",
    side: "right",
    routeRequired: "/dashboard",
  },

  // ── Chart ──────────────────────────────────────────────────────
  {
    id: "chart",
    targetSelector: '[data-tour="chart-toolbar"]',
    title: "Chart View",
    body:
      "Front-month candlesticks resolved from the active instrument's curve. Overlay SMA-20 and EMA-50, swap resolution between 1Y / 1M / 5D / 1D / 1H. Event markers pin EIA reports and other catalysts onto the chart.",
    side: "bottom",
    routeRequired: "/chart",
  },

  // ── Signal Lab ─────────────────────────────────────────────────
  {
    id: "signals",
    targetSelector: '[data-testid="backtest-card"]',
    title: "Signal Lab — honest hit rates",
    body:
      "Four-model ensemble at the top of the page. The Backtest card replays each model against real historical prices under strict look-ahead controls — the hit rates are honest, not curve-fit.",
    side: "top",
    routeRequired: "/signals",
  },

  // ── Scenario Lab ───────────────────────────────────────────────
  {
    id: "scenarios",
    targetSelector: '[data-tour="scenario-shell"]',
    title: "Scenario Lab",
    body:
      "Apply primitive shocks (weather / LNG / production / storage) to a baseline and watch the forecast shift. LLM narrates assumptions, counterarguments, and the data that would validate it. Exportable as a desk-ready PDF.",
    side: "right",
    routeRequired: "/scenarios",
  },

  // ── Journal ────────────────────────────────────────────────────
  {
    id: "journal",
    targetSelector: '[data-tour="journal-shell"]',
    title: "Decision Journal",
    body:
      "Log hypotheses with evidence, conviction, and invalidation criteria. The LLM critiques each entry for decision quality. Mark Hit / Miss / Neutral when the thesis resolves — that's what feeds the calibration loop.",
    side: "right",
    routeRequired: "/journal",
  },

  // ── Paper Trading ─────────────────────────────────────────────
  {
    id: "paper",
    targetSelector: '[data-tour="paper-shell"]',
    title: "Paper Trading",
    body:
      "Simulated round-trips paired to journal entries. Equity curve over 90 days, open positions with live mark-to-market, closed trades with realized PnL. Practice without putting capital at risk.",
    side: "right",
    routeRequired: "/paper",
  },

  // ── Calibration ────────────────────────────────────────────────
  {
    id: "calibration",
    targetSelector: '[data-tour="reliability-diagram"]',
    title: "Decision Calibration",
    body:
      "Reliability diagram across your resolved journal entries: claimed conviction vs actual hit rate. The DQ Coach panel synthesizes per-bucket patterns — what wins, what fails, one actionable suggestion per band.",
    side: "left",
    routeRequired: "/calibration",
  },

  // ── Farewell ──────────────────────────────────────────────────
  {
    id: "done",
    targetSelector: null,
    title: "You're ready",
    body:
      "That's the terminal. Re-launch the tutorial any time from the top bar. Now — what's your thesis?",
    side: "center",
  },
];
