import {
  getPaperEquityCurve,
  listJournalEntries,
  listPaperTrades,
} from "../../../lib/api";
import type { JournalEntriesResponse, JournalEntry } from "../journal/types";
import { PaperShell } from "./PaperShell";
import type {
  EquityCurveResponse,
  EquityPoint,
  Trade,
  TradesResponse,
} from "./types";

function isoDaysAgo(days: number): string {
  const d = new Date(Date.now() - days * 86_400_000);
  return d.toISOString().slice(0, 10);
}

export default async function PaperPage() {
  let openTrades: Trade[] = [];
  let closedTrades: Trade[] = [];
  let equity: EquityPoint[] = [];
  let journalEntries: JournalEntry[] = [];

  const since = isoDaysAgo(90);

  try {
    const resp = (await listPaperTrades({ status: "open" })) as TradesResponse;
    openTrades = resp.trades ?? [];
  } catch {
    // Empty
  }

  try {
    const resp = (await listPaperTrades({
      status: "closed",
    })) as TradesResponse;
    closedTrades = resp.trades ?? [];
  } catch {
    // Empty
  }

  try {
    const resp = (await getPaperEquityCurve(since)) as EquityCurveResponse;
    equity = resp.series ?? [];
  } catch {
    // Empty
  }

  try {
    const resp = (await listJournalEntries(20)) as JournalEntriesResponse;
    journalEntries = resp.entries ?? [];
  } catch {
    // Empty
  }

  return (
    <div className="flex flex-col h-full">
      <PaperShell
        initialOpen={openTrades}
        initialClosed={closedTrades}
        initialEquity={equity}
        journalEntries={journalEntries}
      />
    </div>
  );
}
