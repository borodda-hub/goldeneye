export type ShockType =
  // Natural gas (NG)
  | "weather"
  | "lng_export"
  | "production"
  | "storage"
  // Crude oil (Brent / WTI)
  | "opec_supply"
  | "geopolitical_supply"
  | "demand"
  | "inventory";

export interface WeatherShock {
  type: "weather";
  region: string;
  delta_temp_f: number;
  days: number;
}

export interface LngExportShock {
  type: "lng_export";
  delta_bcfd: number;
  days: number;
}

export interface ProductionShock {
  type: "production";
  delta_bcfd: number;
  days: number;
}

export interface StorageShock {
  type: "storage";
  delta_bcf: number;
  days: number;
}

export interface OpecSupplyShock {
  type: "opec_supply";
  delta_mbpd: number;
  days: number;
}

export interface GeopoliticalSupplyShock {
  type: "geopolitical_supply";
  region: string;
  delta_mbpd: number;
  days: number;
}

export interface DemandShock {
  type: "demand";
  region: string;
  delta_mbpd: number;
  days: number;
}

export interface InventoryShock {
  type: "inventory";
  delta_mmbbl: number;
  days: number;
}

export type Shock =
  | WeatherShock
  | LngExportShock
  | ProductionShock
  | StorageShock
  | OpecSupplyShock
  | GeopoliticalSupplyShock
  | DemandShock
  | InventoryShock;

export interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  instrument: string;
  shocks: Shock[];
}

export interface SafetyEnvelope {
  confidence: string;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

export interface ScenarioResult {
  directional_pressure: "bullish" | "bearish" | "neutral";
  confidence: "low" | "medium" | "high";
  affected_timeframe: string;
  expected_pct_range: { low: number; high: number };
  assumptions: string[];
  counterarguments: string[];
  data_needed_to_validate: string[];
  narrative: string;
  safety: SafetyEnvelope;
}

export interface ScenarioRunResponse {
  run_id: string;
  instrument: string;
  name: string;
  result: ScenarioResult;
}

export interface RecentRun {
  run_id: string;
  created_at: string;
  name: string;
  instrument_id: string;
}
