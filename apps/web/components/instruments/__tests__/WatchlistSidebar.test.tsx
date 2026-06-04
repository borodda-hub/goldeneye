import type { InstrumentRow } from "@/lib/api";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useInstrumentsMock = vi.fn();
const setActiveSymbolMock = vi.fn();
const useActiveInstrumentMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useInstruments: (...args: unknown[]) => useInstrumentsMock(...args),
  useChartBars: () => ({ data: undefined, isLoading: false, error: null }),
}));
vi.mock("@/lib/useActiveInstrument", () => ({
  useActiveInstrument: (...args: unknown[]) => useActiveInstrumentMock(...args),
}));
vi.mock("@/components/instruments/WatchlistSparkline", () => ({
  WatchlistSparkline: () => null,
}));

import { WatchlistSidebar } from "../WatchlistSidebar";

function _row(
  symbol: string,
  name: string,
  overrides: Partial<InstrumentRow["quote"]> = {},
): InstrumentRow {
  return {
    symbol,
    name,
    asset_class: "commodity",
    currency: "USD",
    unit: symbol === "CL" ? "barrel" : "MMBtu",
    metadata: {},
    quote: {
      last_price: symbol === "CL" ? 97.26 : 3.205,
      change_abs: symbol === "CL" ? -1.25 : 0.012,
      change_pct: symbol === "CL" ? -0.0127 : 0.0038,
      front_month_code: symbol === "CL" ? "CLN26" : "NGM26",
      as_of: null,
      ...overrides,
    },
  };
}

beforeEach(() => {
  useInstrumentsMock.mockReset();
  setActiveSymbolMock.mockReset();
  useActiveInstrumentMock.mockReset();
  useActiveInstrumentMock.mockReturnValue({
    activeSymbol: "NG",
    setActiveSymbol: setActiveSymbolMock,
  });
});

describe("WatchlistSidebar", () => {
  it("renders a loading state", () => {
    useInstrumentsMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<WatchlistSidebar />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("renders one row per instrument with symbol + name + price", () => {
    useInstrumentsMock.mockReturnValue({
      data: {
        instruments: [
          _row("NG", "Henry Hub Natural Gas"),
          _row("CL", "WTI Crude Oil"),
        ],
      },
      isLoading: false,
      error: null,
    });
    render(<WatchlistSidebar />);
    expect(screen.getByText("NG")).toBeInTheDocument();
    expect(screen.getByText("CL")).toBeInTheDocument();
    expect(screen.getByText("Henry Hub Natural Gas")).toBeInTheDocument();
    expect(screen.getByText("WTI Crude Oil")).toBeInTheDocument();
    // NG price (under $20 → 3-decimal); CL price ($20+ → 2-decimal)
    expect(screen.getByText("3.205")).toBeInTheDocument();
    expect(screen.getByText("97.26")).toBeInTheDocument();
  });

  it("formats change_pct with arrow + unsigned percent", () => {
    useInstrumentsMock.mockReturnValue({
      data: { instruments: [_row("NG", "NG"), _row("CL", "CL")] },
      isLoading: false,
      error: null,
    });
    render(<WatchlistSidebar />);
    // NG up 0.38% (▲), CL down 1.27% (▼). Arrow is rendered in same span
    // as the pct, so we match the combined text.
    expect(screen.getByText(/▲ 0\.38%/)).toBeInTheDocument();
    expect(screen.getByText(/▼ 1\.27%/)).toBeInTheDocument();
  });

  it("marks the active instrument with aria-current", () => {
    useActiveInstrumentMock.mockReturnValue({
      activeSymbol: "CL",
      setActiveSymbol: setActiveSymbolMock,
    });
    useInstrumentsMock.mockReturnValue({
      data: { instruments: [_row("NG", "NG"), _row("CL", "CL")] },
      isLoading: false,
      error: null,
    });
    render(<WatchlistSidebar />);
    const buttons = screen.getAllByRole("button");
    const cl = buttons.find((b) => b.getAttribute("data-symbol") === "CL");
    const ng = buttons.find((b) => b.getAttribute("data-symbol") === "NG");
    expect(cl).toHaveAttribute("aria-current", "true");
    expect(ng).not.toHaveAttribute("aria-current");
  });

  it("calls setActiveSymbol when a row is clicked", () => {
    useInstrumentsMock.mockReturnValue({
      data: { instruments: [_row("NG", "NG"), _row("CL", "CL")] },
      isLoading: false,
      error: null,
    });
    render(<WatchlistSidebar />);
    fireEvent.click(screen.getAllByRole("button")[1]); // CL row
    expect(setActiveSymbolMock).toHaveBeenCalledWith("CL");
  });

  it("renders em-dash for null prices", () => {
    useInstrumentsMock.mockReturnValue({
      data: {
        instruments: [
          _row("CL", "WTI Crude Oil", {
            last_price: null,
            change_abs: null,
            change_pct: null,
          }),
        ],
      },
      isLoading: false,
      error: null,
    });
    render(<WatchlistSidebar />);
    // last price renders as bare "—"; change values render as "· —"
    // (neutral arrow + em-dash). At least one literal "—" must exist.
    expect(screen.getAllByText(/—/).length).toBeGreaterThan(0);
  });

  it("renders an error state when the query fails", () => {
    useInstrumentsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
    });
    render(<WatchlistSidebar />);
    expect(screen.getByText(/Failed to load watchlist/)).toBeInTheDocument();
  });
});
