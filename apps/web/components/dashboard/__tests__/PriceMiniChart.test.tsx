import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { PriceMiniChart } from "../PriceMiniChart";

// Capture every call to useChartBars so tests can assert resolution + range.
const useChartBarsMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useChartBars: (...args: unknown[]) => useChartBarsMock(...args),
}));

// Recharts uses ResizeObserver which jsdom doesn't ship.
class _StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// @ts-expect-error  shim global
globalThis.ResizeObserver = _StubResizeObserver;

function _sampleBars() {
  return {
    bars: [
      { ts: "2026-05-10T00:00:00", o: 3.0, h: 3.1, l: 2.9, c: 3.05, v: 1000 },
      { ts: "2026-05-11T00:00:00", o: 3.05, h: 3.2, l: 3.0, c: 3.15, v: 1100 },
    ],
    overlays: { sma_20: [], ema_50: [] },
    event_markers: [],
    contract: { code: "NGM26", expiry: "2026-05-31" },
    resolution: "1d",
  };
}

beforeEach(() => {
  useChartBarsMock.mockReset();
  useChartBarsMock.mockReturnValue({ data: _sampleBars(), isLoading: false });
});

describe("PriceMiniChart timeframe controls", () => {
  it("renders the five timeframe buttons", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    for (const key of ["1Y", "1M", "5D", "1D", "1H"]) {
      expect(screen.getByRole("tab", { name: key })).toBeInTheDocument();
    }
  });

  it("defaults to 1M selected", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    expect(screen.getByRole("tab", { name: "1M" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText(/1M Daily/)).toBeInTheDocument();
  });

  it("requests 1d resolution by default", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    const [contract, resolution] = useChartBarsMock.mock.calls.at(-1) as unknown[];
    expect(contract).toBe("NGM26");
    expect(resolution).toBe("1d");
  });

  it("switches to 1H → 1m resolution", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    fireEvent.click(screen.getByRole("tab", { name: "1H" }));
    const [_contract, resolution] = useChartBarsMock.mock.calls.at(-1) as unknown[];
    expect(resolution).toBe("1m");
    expect(screen.getByRole("tab", { name: "1H" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText(/1H 1m/)).toBeInTheDocument();
  });

  it("switches to 5D → 15m resolution", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    fireEvent.click(screen.getByRole("tab", { name: "5D" }));
    const [_contract, resolution] = useChartBarsMock.mock.calls.at(-1) as unknown[];
    expect(resolution).toBe("15m");
    expect(screen.getByText(/5D 15m/)).toBeInTheDocument();
  });

  it("switches to 1D → 5m resolution", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    fireEvent.click(screen.getByRole("tab", { name: "1D" }));
    const [_contract, resolution] = useChartBarsMock.mock.calls.at(-1) as unknown[];
    expect(resolution).toBe("5m");
  });

  it("switches to 1Y → 1d resolution, larger range", () => {
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    fireEvent.click(screen.getByRole("tab", { name: "1Y" }));
    const [_contract, resolution, from, to] = useChartBarsMock.mock.calls.at(
      -1,
    ) as string[];
    expect(resolution).toBe("1d");
    // From-date is well in the past for 1Y; to-date is today (UTC).
    const fromMs = new Date(from).getTime();
    const toMs = new Date(to).getTime();
    const days = (toMs - fromMs) / 86400_000;
    expect(days).toBeGreaterThan(360);
    expect(days).toBeLessThan(370);
  });

  it("shows the empty-state copy when no bars are returned", () => {
    useChartBarsMock.mockReturnValue({
      data: { bars: [], overlays: { sma_20: [], ema_50: [] }, event_markers: [] },
      isLoading: false,
    });
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    expect(screen.getByText(/No data for this range/)).toBeInTheDocument();
  });

  it("shows loading state while the query is pending", () => {
    useChartBarsMock.mockReturnValue({ data: undefined, isLoading: true });
    render(<PriceMiniChart volRegime="normal" contractCode="NGM26" />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });
});
