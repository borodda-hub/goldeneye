import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExpectedRangeCard } from "../ExpectedRangeCard";

const useRangeForecastMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useRangeForecast: (...args: unknown[]) => useRangeForecastMock(...args),
}));

const SAMPLE = {
  symbol: "NG",
  horizon: "1w",
  range: {
    horizon: "1w",
    sigma_daily: 0.02,
    sigma_horizon: 0.045,
    band80_low_pct: -0.057,
    band80_high_pct: 0.057,
    band95_low_pct: -0.088,
    band95_high_pct: 0.088,
    method: "ewma",
    note: "",
  },
  coverage: { cov80: 0.8, cov95: 0.9 },
  safety: {
    confidence: "medium",
    caveats: [],
    as_of: "2026-06-06",
    disclaimer: "x",
  },
};

beforeEach(() => {
  useRangeForecastMock.mockReset();
});

describe("ExpectedRangeCard", () => {
  it("shows the header but no band data while loading", () => {
    useRangeForecastMock.mockReturnValue({ data: undefined, isLoading: true });
    render(<ExpectedRangeCard />);
    expect(screen.getByText("Expected Range")).toBeInTheDocument(); // header always
    expect(screen.queryByText(/95%:/)).not.toBeInTheDocument(); // no data yet
  });

  it("renders the 80% band, 95% band, and walk-forward coverage", () => {
    useRangeForecastMock.mockReturnValue({ data: SAMPLE, isLoading: false });
    render(<ExpectedRangeCard />);
    expect(screen.getByText("+5.7%")).toBeInTheDocument(); // band80 high
    expect(screen.getByText(/95%:/)).toBeInTheDocument();
    expect(
      screen.getByText(/80% band held 80% \(walk-forward\)/),
    ).toBeInTheDocument();
    expect(screen.getByText(/no up\/down call/i)).toBeInTheDocument();
  });

  it("refetches with the chosen horizon when toggled", () => {
    useRangeForecastMock.mockReturnValue({ data: SAMPLE, isLoading: false });
    render(<ExpectedRangeCard />);
    fireEvent.click(screen.getByRole("button", { name: "1M" }));
    expect(useRangeForecastMock).toHaveBeenCalledWith("NG", "1m");
  });
});
