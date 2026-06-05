export type Resolution = "1m" | "5m" | "15m" | "1h" | "1d" | "1w" | "1M";

export type ChartType =
  | "candlestick"
  | "bars"
  | "heikin-ashi"
  | "line"
  | "area"
  | "baseline";

export type RangePreset = "3M" | "6M" | "1Y" | "2Y" | "5Y" | "All";

/** Imperative handle PriceChart exposes so the toolbar can screenshot. */
export interface ChartApi {
  screenshot: () => HTMLCanvasElement | null;
  /** Re-fit all bars into view (reset zoom/pan). */
  fitContent: () => void;
}

export interface Bar {
  ts: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface OverlayPoint {
  ts: string;
  v: number;
}

export interface EventMarkerData {
  ts: string;
  kind: string;
  label: string;
  delta: number;
}

export interface ChartBarsResponse {
  contract: { code: string; expiry: string };
  resolution: string;
  bars: Bar[];
  overlays: { sma_20: OverlayPoint[]; ema_50: OverlayPoint[] };
  event_markers: EventMarkerData[];
}

export interface CurvePoint {
  contract_code: string;
  expiry: string;
  mid: number;
}
