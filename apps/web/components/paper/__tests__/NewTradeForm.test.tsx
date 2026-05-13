import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const mutateMock = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({
    mutate: mutateMock,
    isPending: false,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}));

import { NewTradeForm } from "../NewTradeForm";

describe("NewTradeForm", () => {
  beforeEach(() => {
    mutateMock.mockClear();
  });

  it("renders heading and submit button", () => {
    render(<NewTradeForm journalEntries={[]} />);
    expect(screen.getByText("New Trade")).toBeInTheDocument();
    expect(screen.getByTestId("open-trade-submit")).toBeInTheDocument();
  });

  it("renders side toggle buttons", () => {
    render(<NewTradeForm journalEntries={[]} />);
    expect(screen.getByRole("button", { name: /Long/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Short/i })).toBeInTheDocument();
  });

  it("disables submit when entry price is 0", () => {
    render(<NewTradeForm journalEntries={[]} />);
    expect(screen.getByTestId("open-trade-submit")).toBeDisabled();
  });

  it("enables submit when size and entry price are valid", () => {
    render(<NewTradeForm journalEntries={[]} />);
    const entry = screen.getByLabelText(/Entry Price/i);
    fireEvent.change(entry, { target: { value: "3.45" } });
    expect(screen.getByTestId("open-trade-submit")).not.toBeDisabled();
  });

  it("renders journal entry options when provided", () => {
    const entries = [
      {
        id: "j1",
        created_at: "2026-05-10T14:30:00Z",
        instrument_id: "ng-id",
        hypothesis: "Cold snap rally setup",
        evidence: [],
        confidence_pct: 65,
        planned_action: null,
        risk_factors: null,
        invalidation_criteria: null,
        outcome: null,
        reflection: null,
        llm_review: null,
        resolved_direction: null,
        thesis_id_at_write: null,
        thesis_conviction_at_write: null,
      },
    ];
    render(<NewTradeForm journalEntries={entries} />);
    expect(screen.getByText(/Cold snap rally setup/)).toBeInTheDocument();
    expect(screen.getByText(/None/)).toBeInTheDocument();
  });
});
