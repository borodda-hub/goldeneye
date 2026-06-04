import type { InstrumentRow } from "@/lib/api";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useInstrumentsMock = vi.fn();
const setActiveSymbolMock = vi.fn();
const useActiveInstrumentMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useInstruments: (...args: unknown[]) => useInstrumentsMock(...args),
}));
vi.mock("@/lib/useActiveInstrument", () => ({
  useActiveInstrument: (...args: unknown[]) => useActiveInstrumentMock(...args),
}));

import { InstrumentSwitcher } from "../InstrumentSwitcher";

function _row(symbol: string, name: string): InstrumentRow {
  return {
    symbol,
    name,
    asset_class: "commodity",
    currency: "USD",
    unit: symbol === "CL" ? "barrel" : "MMBtu",
    metadata: {},
    quote: {
      last_price: null,
      change_abs: null,
      change_pct: null,
      front_month_code: null,
      as_of: null,
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
  useInstrumentsMock.mockReturnValue({
    data: {
      instruments: [_row("NG", "Natural Gas"), _row("CL", "WTI Crude Oil")],
    },
    isLoading: false,
    error: null,
  });
});

describe("InstrumentSwitcher", () => {
  it("renders the active symbol + name on the trigger button", () => {
    render(<InstrumentSwitcher />);
    const button = screen.getByTestId("instrument-switcher");
    expect(button).toHaveTextContent("NG");
    expect(button).toHaveTextContent("Natural Gas");
  });

  it("opens a listbox when clicked", () => {
    render(<InstrumentSwitcher />);
    fireEvent.click(screen.getByTestId("instrument-switcher"));
    expect(
      screen.getByRole("listbox", { name: /Instruments/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("calls setActiveSymbol with the picked symbol", () => {
    render(<InstrumentSwitcher />);
    fireEvent.click(screen.getByTestId("instrument-switcher"));
    fireEvent.click(screen.getByRole("option", { selected: false }));
    expect(setActiveSymbolMock).toHaveBeenCalledWith("CL");
  });

  it("marks the active row with aria-selected", () => {
    render(<InstrumentSwitcher />);
    fireEvent.click(screen.getByTestId("instrument-switcher"));
    const selected = screen.getByRole("option", { selected: true });
    expect(selected).toHaveTextContent("NG");
  });
});
