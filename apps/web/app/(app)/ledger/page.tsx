import { getLedger } from "../../../lib/api";
import { LedgerShell } from "./LedgerShell";
import type { LedgerDecision, LedgerListResponse } from "./types";

export default async function LedgerPage() {
  let decisions: LedgerDecision[] = [];

  try {
    const resp = (await getLedger()) as LedgerListResponse;
    decisions = resp.decisions ?? [];
  } catch {
    // Server-side prefetch failed; render empty list
  }

  return (
    <div className="flex flex-col h-full">
      <LedgerShell initialDecisions={decisions} />
    </div>
  );
}
