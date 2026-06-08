import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ExpectedRange } from "../ExpectedRange";

const useRangeForecastMock = vi.fn();
const useInstrumentsMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useRangeForecast: (...args: unknown[]) => useRangeForecastMock(...args),
  useInstruments: (...args: unknown[]) => useInstrumentsMock(...args),
}));

const range = {
  horizon: "1w",
  sigma_daily: 0.023,
  sigma_horizon: 0.0514,
  band80_low_pct: -0.066,
  band80_high_pct: 0.066,
  band95_low_pct: -0.101,
  band95_high_pct: 0.101,
  method: "ewma",
  note: "…",
};

const forecast = {
  symbol: "NG",
  horizon: "1w",
  estimator: "ewma",
  range,
  coverage: { cov80: 0.8, cov95: 0.94, n_eff: 140 },
  forward_vol_corr: 0.42,
  safety: { confidence: "medium", caveats: [], as_of: "", disclaimer: "" },
};

beforeEach(() => {
  useRangeForecastMock.mockReset();
  useInstrumentsMock.mockReset();
  useInstrumentsMock.mockReturnValue({
    data: { instruments: [{ symbol: "NG", quote: { last_price: 3.2 } }] },
  });
});

describe("ExpectedRange", () => {
  it("renders nothing until the forecast resolves (graceful for un-deployed API)", () => {
    useRangeForecastMock.mockReturnValue({ data: undefined });
    useInstrumentsMock.mockReturnValue({ data: undefined });
    const { container } = render(<ExpectedRange symbol="NG" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows daily vol, walk-forward coverage, and forward-vol correlation", () => {
    useRangeForecastMock.mockReturnValue({ data: forecast });
    render(<ExpectedRange symbol="NG" />);
    expect(screen.getByText("2.30%")).toBeInTheDocument(); // daily vol
    expect(screen.getByText("80%")).toBeInTheDocument(); // coverage
    expect(screen.getByText(/140 windows/)).toBeInTheDocument();
    expect(screen.getByText("+0.42")).toBeInTheDocument(); // forward-vol corr
  });

  it("derives the $ band from the instrument spot price", () => {
    useRangeForecastMock.mockReturnValue({ data: forecast });
    render(<ExpectedRange symbol="NG" />);
    // 3.20 * (1 ± 0.066) → 2.989 – 3.411 (spot < 20 → 3 decimals)
    expect(screen.getByText(/2\.989/)).toBeInTheDocument();
    expect(screen.getByText(/3\.411/)).toBeInTheDocument();
  });

  it("states it makes no directional claim", () => {
    useRangeForecastMock.mockReturnValue({ data: forecast });
    render(<ExpectedRange symbol="NG" />);
    expect(screen.getByText(/Range only — no directional/)).toBeInTheDocument();
  });

  it("badges the active estimator and passes it to the query", () => {
    useRangeForecastMock.mockReturnValue({
      data: { ...forecast, estimator: "har_log" },
    });
    render(<ExpectedRange symbol="NG" estimator="har_log" />);
    expect(screen.getByText("log-HAR")).toBeInTheDocument();
    expect(useRangeForecastMock).toHaveBeenCalledWith("NG", "1w", "har_log");
  });
});
