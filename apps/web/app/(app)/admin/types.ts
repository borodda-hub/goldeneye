export interface AdapterRollup {
  name: string;
  status: "ok" | "degraded" | "down";
  last_success: string | null;
  lag_minutes: number | null;
  rows_ingested: number | null;
  error: string | null;
  expected_cadence_minutes: number;
}

export interface ModelRollup {
  name: string;
  last_forecast_at: string | null;
  sample_count_7d: number;
}

export interface DataHealth {
  adapters: AdapterRollup[];
  models: ModelRollup[];
  /**
   * Server-side env-var presence flags. Values are never returned — only
   * whether the var is set in the FastAPI process's environment.
   * Optional for backwards compat with older snapshots.
   */
  env_flags?: Record<string, boolean>;
}

export interface Alert {
  id: string;
  created_at: string;
  kind: string;
  severity: string;
  payload: Record<string, unknown>;
  read: boolean;
  acknowledged: boolean;
}

export interface AlertsResponse {
  alerts: Alert[];
}
