export interface Trade {
  id: string;
  opened_at: string;
  closed_at: string | null;
  instrument_id: string;
  contract_id: string | null;
  side: "long" | "short";
  size_contracts: number;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  status: "open" | "closed" | "cancelled";
  rationale: string | null;
  outcome_pnl: number | null;
  reflection: string | null;
  journal_ref: string | null;
}

export interface TradesResponse {
  trades: Trade[];
}

export interface EquityPoint {
  date: string;
  equity: number;
}

export interface EquityCurveResponse {
  series: EquityPoint[];
}

export interface PriceTick {
  ts: string;
  price: number;
}

export const NG_TICK_VALUE_USD = 10_000;
