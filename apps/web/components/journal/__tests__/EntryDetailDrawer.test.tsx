import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

// Stub the patch hook used by the embedded ResolutionPicker so tests render
// without a QueryClientProvider.
vi.mock("@/lib/queries", () => ({
  usePatchJournalEntry: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { EntryDetailDrawer } from "../EntryDetailDrawer";
import type { JournalEntry } from "../../../app/(app)/journal/types";

const baseEntry: JournalEntry = {
  id: "entry-1",
  created_at: "2026-05-10T14:30:00Z",
  instrument_id: "ng-id",
  hypothesis: "Cold snap likely tightens balances.",
  evidence: [
    { source: "NWS", summary: "Polar vortex anomaly", weight: 0.7 },
  ],
  confidence_pct: 65,
  planned_action: "Watch storage report Thursday",
  risk_factors: ["LNG demand surprise"],
  invalidation_criteria: "Mild revision in 6-10 day outlook",
  outcome: null,
  reflection: null,
  llm_review: {
    text: "Assumption: weather forecast is reliable.\nAssumption: storage draw materializes.\nRisk: LNG demand misread.",
    safety: {
      confidence: "medium",
      caveats: ["Hypothetical reasoning only."],
      as_of: "2026-05-10T15:00:00Z",
      disclaimer: "research prototype",
    },
  },
  resolved_direction: null,
  thesis_id_at_write: null,
  thesis_conviction_at_write: null,
};

describe("EntryDetailDrawer", () => {
  it("renders the hypothesis", () => {
    render(<EntryDetailDrawer entry={baseEntry} onClose={() => {}} />);
    expect(screen.getByText(/Cold snap likely tightens/)).toBeInTheDocument();
  });

  it("renders confidence percentage", () => {
    render(<EntryDetailDrawer entry={baseEntry} onClose={() => {}} />);
    expect(screen.getByText("65%")).toBeInTheDocument();
  });

  it("renders LLM review bullets split on newlines", () => {
    render(<EntryDetailDrawer entry={baseEntry} onClose={() => {}} />);
    const bullets = screen.getByTestId("llm-review-bullets");
    expect(bullets.querySelectorAll("li").length).toBe(3);
    expect(bullets.textContent).toMatch(/weather forecast is reliable/);
  });

  it("shows review pending when llm_review is null", () => {
    render(
      <EntryDetailDrawer
        entry={{ ...baseEntry, llm_review: null }}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText(/Review pending/)).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<EntryDetailDrawer entry={baseEntry} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText(/Close detail/i));
    expect(onClose).toHaveBeenCalled();
  });

  it("does not crash on legacy structured llm_review without a text field", () => {
    const legacyEntry = {
      ...baseEntry,
      llm_review: {
        implicit_assumption: "Storage draw will materialize as forecast.",
        missing_risk: "LNG export surprise not weighted.",
        confidence_assessment: "65% is consistent with the evidence.",
        invalidation_quality: "Time-bound and testable.",
        process_improvement: "Add a re-evaluation trigger date.",
        strengthening_evidence: "Basis differentials at NE hubs.",
      },
    } as unknown as JournalEntry;
    render(<EntryDetailDrawer entry={legacyEntry} onClose={() => {}} />);
    const bullets = screen.getByTestId("llm-review-bullets");
    expect(bullets.querySelectorAll("li").length).toBe(6);
    expect(bullets.textContent).toMatch(/Implicit assumption/);
    expect(bullets.textContent).toMatch(/Missing risk/);
  });

  it("does not crash when llm_review is a non-string non-null garbage value", () => {
    const broken = {
      ...baseEntry,
      llm_review: 12345 as unknown,
    } as unknown as JournalEntry;
    render(<EntryDetailDrawer entry={broken} onClose={() => {}} />);
    expect(screen.getByText(/Review pending/)).toBeInTheDocument();
  });
});
