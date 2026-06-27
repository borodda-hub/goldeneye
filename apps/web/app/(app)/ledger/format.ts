// Phase B4 — pure helpers for reading the ledger's variant JSON payloads.
// Kept separate from the shell so the defensive narrowing is unit-tested.
import type { LedgerDecision } from "./types";

export function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}

export function asString(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

export function asNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function asBool(v: unknown): boolean | null {
  return typeof v === "boolean" ? v : null;
}

/** The decision's headline hypothesis, taken from its `created` event. */
export function decisionHypothesis(d: LedgerDecision): string {
  const created = d.events.find((e) => e.event_type === "created");
  const inputs = asRecord(asRecord(created?.payload).user_inputs);
  return asString(inputs.hypothesis) ?? "(no hypothesis recorded)";
}

/** When the decision was made — the `created` event's domain time. */
export function decisionTimestamp(d: LedgerDecision): string | null {
  const created = d.events.find((e) => e.event_type === "created");
  return created?.occurred_at ?? d.events[0]?.occurred_at ?? null;
}

export function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

/** A move stored as a fraction (0.034) → "+3.40%". */
export function fmtFraction(v: number | null): string {
  if (v === null) return "—";
  const pct = v * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

export function fmtPrice(v: number | null): string {
  return v === null ? "—" : v.toFixed(3);
}
