"use client";

import { NotebookPen } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "../../../components/PageHeader";
import { SampleDeskBanner } from "../../../components/SampleDeskBanner";
import { EntryDetailDrawer } from "../../../components/journal/EntryDetailDrawer";
import { EntryList } from "../../../components/journal/EntryList";
import { NewEntryForm } from "../../../components/journal/NewEntryForm";
import { useJournalEntries } from "../../../lib/queries";
import { useActiveInstrument } from "../../../lib/useActiveInstrument";
import type { JournalEntriesResponse, JournalEntry } from "./types";

interface Props {
  initialEntries: JournalEntry[];
}

export function JournalShell({ initialEntries }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { activeSymbol } = useActiveInstrument();

  const { data } = useJournalEntries(20, activeSymbol);
  const entries =
    (data as JournalEntriesResponse | undefined)?.entries ?? initialEntries;

  const selected = entries.find((e) => e.id === selectedId) ?? null;

  return (
    <div className="stagger flex flex-col gap-4" data-tour="journal-shell">
      <PageHeader
        icon={NotebookPen}
        title="Decision Journal"
        subtitle="Hypothesis log with AI assumption review"
      />

      <SampleDeskBanner />

      {/* Two-column on desktop; stacks (list, then detail/form) below `lg`. */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="flex-1 min-w-0">
          <EntryList
            entries={entries}
            selectedId={selectedId}
            onSelect={(id) => setSelectedId(id)}
          />
        </div>
        <div className="w-full lg:w-96 lg:shrink-0">
          {selected ? (
            <EntryDetailDrawer
              entry={selected}
              onClose={() => setSelectedId(null)}
            />
          ) : (
            <NewEntryForm onCreated={(id) => setSelectedId(id)} />
          )}
        </div>
      </div>
    </div>
  );
}
