import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { Trade } from "../../../app/(app)/paper/types";

const useChannelMock = vi.fn();
vi.mock("../../../lib/realtime", () => ({
  useChannel: (...args: unknown[]) => useChannelMock(...args),
}));

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

import { OpenPositionsTable, computeMtm } from "../OpenPositionsTable";

const longTrade: Trade = {
  id: "t1",
  opened_at: "2026-05-10T12:00:00Z",
  closed_at: null,
  instrument_id: "ng-id",
  contract_id: null,
  side: "long",
  size_contracts: 2,
  entry_price: 3.45,
  exit_price: null,
  stop_loss: 3.3,
  take_profit: 3.7,
  status: "open",
  rationale: null,
  outcome_pnl: null,
  reflection: null,
  journal_ref: null,
};

describe("computeMtm", () => {
  it("computes positive PnL for long going up", () => {
    expect(computeMtm(longTrade, 3.5)).toBeCloseTo(0.05 * 2 * 10000, 0);
  });

  it("flips sign for short", () => {
    expect(computeMtm({ ...longTrade, side: "short" }, 3.5)).toBeCloseTo(
      -0.05 * 2 * 10000,
      0,
    );
  });
});

describe("OpenPositionsTable", () => {
  beforeEach(() => {
    useChannelMock.mockReset();
    mutateMock.mockClear();
  });

  it("renders heading and column labels", () => {
    useChannelMock.mockReturnValue({ data: null, status: "disconnected" });
    render(<OpenPositionsTable trades={[]} />);
    expect(screen.getByText("Open Positions")).toBeInTheDocument();
    expect(screen.getByText(/MTM PnL/)).toBeInTheDocument();
  });

  it("shows empty state when no trades", () => {
    useChannelMock.mockReturnValue({ data: null, status: "disconnected" });
    render(<OpenPositionsTable trades={[]} />);
    expect(screen.getByText("No open positions.")).toBeInTheDocument();
  });

  it('renders "—" for MTM when live price is null', () => {
    useChannelMock.mockReturnValue({ data: null, status: "disconnected" });
    render(<OpenPositionsTable trades={[longTrade]} />);
    expect(screen.getByTestId("mtm-pnl").textContent).toBe("—");
  });

  it("renders positive PnL with text-up class for winning long", () => {
    useChannelMock.mockReturnValue({
      data: { ts: "2026-05-10T12:30:00Z", price: 3.5 },
      status: "connected",
    });
    render(<OpenPositionsTable trades={[longTrade]} />);
    const cell = screen.getByTestId("mtm-pnl");
    expect(cell.textContent).toContain("+$");
    expect(cell.className).toContain("text-up");
  });

  it("renders close button per row", () => {
    useChannelMock.mockReturnValue({ data: null, status: "disconnected" });
    render(<OpenPositionsTable trades={[longTrade]} />);
    expect(screen.getByTestId("close-trade-btn")).toBeInTheDocument();
  });
});
