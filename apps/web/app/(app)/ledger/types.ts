// Phase B4 — decision/audit ledger view types.
// Mirror the backend response models in apps/api/routers/ledger.py
// (LedgerEventOut / LedgerDecisionOut / LedgerListOut). The generated
// `packages/contracts` carries the same shapes; these hand-written types follow
// the house pattern (web reads via lib/api.ts, not the generated client).

export type LedgerEventType = "created" | "resolved" | "amended";

export interface LedgerEvent {
  seq: number;
  decision_id: string;
  event_type: LedgerEventType;
  occurred_at: string;
  recorded_at: string;
  source: string;
  // The immutable snapshot — shape varies by event_type (see the payload
  // builders in apps/api/services/ledger.py). Read defensively.
  payload: Record<string, unknown>;
  prev_hash: string | null;
  row_hash: string;
}

export interface LedgerDecision {
  decision_id: string;
  events: LedgerEvent[];
  // Hash-chain integrity — false means an out-of-band edit was detected.
  chain_ok: boolean;
  broken_at_seq: number | null;
}

export interface LedgerListResponse {
  decisions: LedgerDecision[];
}
