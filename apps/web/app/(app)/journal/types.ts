export interface Evidence {
  source: string;
  summary: string;
  weight: number;
}

export interface SafetyEnvelope {
  confidence: string;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

export interface LlmReview {
  text: string;
  safety: SafetyEnvelope;
}

export interface JournalEntry {
  id: string;
  created_at: string;
  instrument_id: string;
  hypothesis: string;
  evidence: Evidence[];
  confidence_pct: number;
  planned_action: string | null;
  risk_factors: string[] | null;
  invalidation_criteria: string | null;
  outcome: string | null;
  reflection: string | null;
  llm_review: LlmReview | null;
}

export interface JournalEntriesResponse {
  entries: JournalEntry[];
}
