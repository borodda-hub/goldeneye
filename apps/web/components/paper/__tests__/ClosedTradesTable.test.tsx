import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ClosedTradesTable } from "../ClosedTradesTable";
import type { Trade } from "../../../app/(app)/paper/types";

const trades: Trade[] = [
  {
    id: "t1",
    opened_at: "2026-05-08T12:00:00Z",
    closed_at: "2026-05-09T18:00:00Z",
    instrument_id: "ng-id",
    contract_id: null,
    side: "long",
    size_contracts: 2,
    entry_price: 3.45,
    exit_price: 3.55,
    stop_loss: null,
    take_profit: null,
    status: "closed",
    rationale: null,
    outcome_pnl: 2000,
    reflection: null,
    journal_ref: null,
  },
  {
    id: "t2",
    opened_at: "2026-05-05T12:00:00Z",
    closed_at: "2026-05-06T18:00:00Z",
    instrument_id: "ng-id",
    contract_id: null,
    side: "short",
    size_contracts: 1,
    entry_price: 3.6,
    exit_price: 3.7,
    stop_loss: null,
    take_profit: null,
    status: "closed",
    rationale: null,
    outcome_pnl: -1000,
    reflection: null,
    journal_ref: null,
  },
];

describe("ClosedTradesTable", () => {
  it("renders Closed Trades heading", () => {
    render(<ClosedTradesTable trades={trades} />);
    expect(screen.getByText("Closed Trades")).toBeInTheDocument();
  });

  it("renders the Export CSV button", () => {
    render(<ClosedTradesTable trades={trades} />);
    expect(screen.getByTestId("export-csv")).toBeInTheDocument();
  });

  it("disables CSV button when no trades", () => {
    render(<ClosedTradesTable trades={[]} />);
    expect(screen.getByTestId("export-csv")).toBeDisabled();
  });

  it("shows winning PnL with text-up and losing with text-down", () => {
    render(<ClosedTradesTable trades={trades} />);
    expect(screen.getByText("+$2000").className).toContain("text-up");
    expect(screen.getByText("-$1000").className).toContain("text-down");
  });

  it("toggles sort indicator when clicking column header", () => {
    render(<ClosedTradesTable trades={trades} />);
    const header = screen.getByText(/PnL/);
    fireEvent.click(header);
    expect(header.textContent).toMatch(/PnL\s*▼|PnL\s*▲/);
  });

  it("triggers CSV download via createObjectURL", () => {
    const createMock = vi.fn(() => "blob:fake");
    const revokeMock = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      value: createMock,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeMock,
      configurable: true,
    });
    render(<ClosedTradesTable trades={trades} />);
    fireEvent.click(screen.getByTestId("export-csv"));
    expect(createMock).toHaveBeenCalled();
  });
});
