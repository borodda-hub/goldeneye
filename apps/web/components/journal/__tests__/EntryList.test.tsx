import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { EntryList } from "../EntryList";
import type { JournalEntry } from "../../../app/(app)/journal/types";

const entries: JournalEntry[] = [
  {
    id: "entry-1",
    created_at: "2026-05-10T14:30:00Z",
    instrument_id: "ng-id",
    hypothesis: "Cold snap will tighten balances next week.",
    evidence: [],
    confidence_pct: 75,
    planned_action: null,
    risk_factors: null,
    invalidation_criteria: null,
    outcome: null,
    reflection: null,
    llm_review: {
      text: "Assumption A. Assumption B.",
      safety: {
        confidence: "medium",
        caveats: [],
        as_of: "2026-05-10T15:00:00Z",
        disclaimer: "research",
      },
    },
  },
  {
    id: "entry-2",
    created_at: "2026-05-09T10:00:00Z",
    instrument_id: "ng-id",
    hypothesis: "Storage build above consensus is bearish.",
    evidence: [],
    confidence_pct: 20,
    planned_action: null,
    risk_factors: null,
    invalidation_criteria: null,
    outcome: null,
    reflection: null,
    llm_review: null,
  },
];

describe("EntryList", () => {
  it("renders each entry hypothesis", () => {
    render(
      <EntryList entries={entries} selectedId={null} onSelect={() => {}} />,
    );
    expect(screen.getByText(/Cold snap will tighten/)).toBeInTheDocument();
    expect(screen.getByText(/Storage build above/)).toBeInTheDocument();
  });

  it("renders confidence percentage labels", () => {
    render(
      <EntryList entries={entries} selectedId={null} onSelect={() => {}} />,
    );
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
  });

  it("calls onSelect with entry id when clicked", () => {
    const onSelect = vi.fn();
    render(
      <EntryList entries={entries} selectedId={null} onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByText(/Cold snap will tighten/));
    expect(onSelect).toHaveBeenCalledWith("entry-1");
  });

  it("marks the review indicator dot as present when llm_review exists", () => {
    render(
      <EntryList entries={entries} selectedId={null} onSelect={() => {}} />,
    );
    const dots = screen.getAllByTestId("review-dot");
    expect(dots[0].getAttribute("data-has-review")).toBe("true");
    expect(dots[1].getAttribute("data-has-review")).toBe("false");
  });

  it("shows empty state when no entries", () => {
    render(<EntryList entries={[]} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText(/No journal entries yet/)).toBeInTheDocument();
  });
});
