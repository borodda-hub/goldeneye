export interface Instrument {
  symbol: string;
  name: string;
  currency: string;
  unit: string;
}

export interface FrontMonth {
  contract_code: string;
  last_price: number;
  change_abs: number;
  change_pct: number;
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
}

export interface SafetyEnvelope {
  confidence: Confidence;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

export interface DashboardSummary {
  instrument: Instrument;
  front_month: FrontMonth;
  vol_regime: VolRegime;
  directional_bias: DirectionalBias;
  futures_curve: FuturesCurvePoint[];
  recent_events: RecentEvent[];
  ai_summary: string;
  safety: SafetyEnvelope;
}
