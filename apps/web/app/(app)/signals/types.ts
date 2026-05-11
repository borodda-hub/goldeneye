export interface EnsembleData {
  direction: "bullish" | "bearish" | "neutral";
  confidence: "low" | "medium" | "high";
  vol_regime: string | null;
  expected_pct: number | null;
  range: { low_pct: number; high_pct: number } | null;
  agreement: {
    bullish: number;
    bearish: number;
    neutral: number;
    total: number;
    input_diversity: "low" | "medium" | "high";
  };
  confidence_rationale: string[];
  caveats: string[];
}

export interface ModelResult {
  model_name: string;
  horizon: string;
  direction: "bullish" | "bearish" | "neutral";
  confidence: "low" | "medium" | "high";
  expected_pct: number | null;
  inputs_used: string[];
  range: { low_pct: number | null; high_pct: number | null };
  supporting: Array<{ factor: string; weight: number; note: string }>;
  contradicting: Array<{ factor: string; weight: number; note: string }>;
}

export interface SafetyEnvelope {
  confidence: string;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

export interface CurrentSignal {
  instrument: string;
  ensemble: EnsembleData;
  models: ModelResult[];
  explanation: string;
  safety: SafetyEnvelope;
}

export interface HistoryRow {
  id: string;
  generated_at: string;
  horizon_end: string;
  model_name: string;
  horizon: string;
  direction: "bullish" | "bearish" | "neutral";
  confidence: "low" | "medium" | "high";
  expected_pct: number | null;
  vol_regime: string | null;
  outcome: "hit" | "miss" | "indeterminate" | "neutral" | "pending";
  realized_pct: number | null;
  delta_from_expected_pct: number | null;
  scored_at: string | null;
}

export interface SignalHistory {
  instrument: string;
  rows: HistoryRow[];
}
