export interface Instrument {
  symbol: string;
  name: string;
  currency: string;
  unit: string;
}

export interface FrontMonth {
  contract_code: string;
  // The backend serializer can return null for any of these when the market
  // adapter has no live data yet (e.g. Yahoo cache hasn't warmed up for a
  // newly-listed contract). Renderers must guard.
  last_price: number | null;
  change_abs: number | null;
  change_pct: number | null;
  as_of: string;
}

export type VolRegime = "compressed" | "normal" | "elevated" | "crisis";

export type Direction = "bullish" | "bearish" | "neutral";

export type Confidence = "low" | "medium" | "high";

export interface DirectionalBias {
  direction: Direction;
  confidence: Confidence;
}

export interface FuturesCurvePoint {
  contract_code: string;
  expiry: string;
  mid: number;
}

export interface RecentEvent {
  id: string;
  published_at: string;
  headline: string;
  category: string;
  impact_score: number;
  /** Source-feed URL — present for live RSS items, null for legacy seeded
   * fixtures. The UI renders the headline as an anchor when this is set. */
  url?: string | null;
  source?: string | null;
}

export interface SafetyEnvelope {
  confidence: Confidence;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

export type CurveShape = "contango" | "backwardation" | "mixed" | "unknown";

export interface AiThesis {
  thesis: string;
  drivers: string[];
  watch: string[];
  curve_shape: CurveShape;
  safety: SafetyEnvelope;
}

export interface DashboardSummary {
  instrument: Instrument;
  front_month: FrontMonth;
  vol_regime: VolRegime;
  directional_bias: DirectionalBias;
  futures_curve: FuturesCurvePoint[];
  recent_events: RecentEvent[];
  ai_summary: string;
  ai_thesis?: AiThesis | null;
  safety: SafetyEnvelope;
}
