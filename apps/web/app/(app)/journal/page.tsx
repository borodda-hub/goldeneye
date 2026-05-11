import { listJournalEntries } from "../../../lib/api";
import { JournalShell } from "./JournalShell";
import type { JournalEntriesResponse, JournalEntry } from "./types";

export default async function JournalPage() {
  let entries: JournalEntry[] = [];

  try {
    const resp = (await listJournalEntries(20)) as JournalEntriesResponse;
    entries = resp.entries ?? [];
  } catch {
    // Server-side prefetch failed; render empty list
  }

  return (
    <div className="flex flex-col h-full">
      <JournalShell initialEntries={entries} />
    </div>
  );
}
