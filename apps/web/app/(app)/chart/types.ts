export type Resolution = "1m" | "5m" | "15m" | "1h" | "1d";

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
