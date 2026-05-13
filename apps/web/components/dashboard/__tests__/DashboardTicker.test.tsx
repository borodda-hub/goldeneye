import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { TickerItem } from "@/lib/api";

const useTickerQuotesMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useTickerQuotes: (...args: unknown[]) => useTickerQuotesMock(...args),
}));

import { DashboardTicker } from "../DashboardTicker";

const _items: TickerItem[] = [
  { symbol: "^GSPC", label: "S&P 500", last_price: 5482.13, change_pct: 0.0042 },
  { symbol: "NG=F", label: "Nat Gas", last_price: 3.205, change_pct: -0.0125 },
  { symbol: "CL=F", label: "WTI Crude", last_price: 78.42, change_pct: 0.0087 },
];

beforeEach(() => {
  useTickerQuotesMock.mockReset();
});

describe("DashboardTicker", () => {
  it("renders a loading state", () => {
    useTickerQuotesMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<DashboardTicker />);
    expect(screen.getByLabelText(/Market ticker loading/i)).toBeInTheDocument();
  });

  it("renders an unavailable state when error", () => {
    useTickerQuotesMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
    });
    render(<DashboardTicker />);
    expect(screen.getByLabelText(/Market ticker unavailable/i)).toBeInTheDocument();
  });

  it("renders the basket twice for the seamless loop", () => {
    useTickerQuotesMock.mockReturnValue({
      data: { items: _items, cached: false },
      isLoading: false,
      error: null,
    });
    render(<DashboardTicker />);
    // 3 items × 2 copies = 6 occurrences for each label.
    expect(screen.getAllByText("S&P 500")).toHaveLength(2);
    expect(screen.getAllByText("Nat Gas")).toHaveLength(2);
    expect(screen.getAllByText("WTI Crude")).toHaveLength(2);
  });

  it("color-codes change_pct (up green, down red)", () => {
    useTickerQuotesMock.mockReturnValue({
      data: { items: _items, cached: false },
      isLoading: false,
      error: null,
    });
    const { container } = render(<DashboardTicker />);
    // The Nat Gas row is negative — must have text-down class somewhere.
    expect(container.innerHTML).toContain("text-down");
    // S&P up — text-up class.
    expect(container.innerHTML).toContain("text-up");
  });

  it("renders the em-dash for missing prices", () => {
    useTickerQuotesMock.mockReturnValue({
      data: {
        items: [
          {
            symbol: "X",
            label: "Missing",
            last_price: null,
            change_pct: null,
          },
        ],
        cached: false,
      },
      isLoading: false,
      error: null,
    });
    render(<DashboardTicker />);
    // Two copies × 2 dashes (price + change_pct) = 4 em-dashes
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
