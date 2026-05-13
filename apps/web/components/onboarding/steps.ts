/**
 * Walkthrough step definitions.  Each step targets a DOM element via CSS
 * selector (preferred: `data-testid` attributes already present on the
 * dashboard).  When `targetSelector` is null the step renders as a centered
 * modal — used for the welcome and farewell screens.
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
  /** Optional URL we should navigate to before this step runs. */
  routeRequired?: string;
}

export const DASHBOARD_TOUR: WalkthroughStep[] = [
  {
    id: "welcome",
    targetSelector: null,
    title: "Welcome to Goldeneye",
    body:
      "A six-stop tour of the terminal. Esc dismisses; ← / → step. You can re-launch this any time from the top bar.",
    side: "center",
    routeRequired: "/dashboard",
  },
  {
    id: "watchlist",
    targetSelector: '[aria-label="Watchlist"]',
    title: "Watchlist",
    body:
      "Click an instrument to switch context. Every page on the terminal — Signal Lab, Calibration, Journal, Paper Trading — refetches against your pick. URL and localStorage keep the selection across reloads.",
    side: "right",
  },
  {
    id: "working-thesis",
    targetSelector: '[data-tour="working-thesis"]',
    title: "Working Thesis",
    body:
      "Your current view as a first-class object. Supporting + contradicting evidence auto-populate from the latest ensemble forecast and scenario run. Your conviction percentage feeds the calibration loop.",
    side: "bottom",
  },
  {
    id: "signal-quality",
    targetSelector: '[data-testid="signal-quality-chip"]',
    title: "Signal Quality grade",
    body:
      "Composite of four sub-scores: input diversity, model agreement, regime stability, and data freshness. Click the chip for the breakdown.",
    side: "bottom",
  },
  {
    id: "resize",
    targetSelector: '[data-testid="resizable-split-handle"]',
    title: "Resize the panes",
    body:
      "Drag this hairline to rebalance the chart and the directional bias card. Width persists per-user. Keyboard: focus + ← / → nudges 16 px.",
    side: "right",
  },
  {
    id: "ticker",
    targetSelector: '[data-testid="dashboard-ticker"]',
    title: "Macro context",
    body:
      "Indices, commodities, and macro pairs scrolling at the foot of the page. Hover to pause. Yahoo-delayed quotes, refreshed every five minutes.",
    side: "top",
  },
  {
    id: "done",
    targetSelector: null,
    title: "You're set",
    body:
      "Explore Signal Lab, Scenario Lab, Journal, Paper Trading, and Calibration from the side nav. Each page respects your active instrument. The terminal is yours.",
    side: "center",
  },
];
