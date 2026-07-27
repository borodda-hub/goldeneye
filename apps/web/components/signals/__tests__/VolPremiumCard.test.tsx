import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useVolPremiumMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useVolPremium: () => useVolPremiumMock(),
}));

import { VolPremiumCard } from "../VolPremiumCard";

const SUPPORTED = {
  symbol: "CL",
  supported: true,
  pair: { underlying: "USO", iv_index: "^OVX" },
  current: {
    date: "2026-07-25",
    sigma_f: 0.31,
    iv: 0.36,
    spread: -0.05,
    percentile: 22.0,
    bucket: "low" as const,
  },
  ship_gate: true,
  g1: {
    mae_forecast: 0.1027,
    mae_iv: 0.1079,
    delta: -0.005,
    se: 0.007,
    passes: false,
  },
  terciles: {
    low: { mean: 0.076, se: 0.028, n: 219 },
    mid: { mean: 0.055, se: 0.012, n: 166 },
    high: { mean: 0.02, se: 0.025, n: 112 },
  },
  timing_tested: true,
  sample: {
    n: 549,
    n_eff: 131,
    span: ["2015-08-07", "2026-06-12"],
    mean_premium: 0.055,
  },
};

describe("VolPremiumCard", () => {
  it("renders NOTHING for unsupported symbols — absence is the honest state", () => {
    useVolPremiumMock.mockReturnValue({
      data: { symbol: "NG", supported: false, reason: "no free IV index" },
    });
    const { container } = render(<VolPremiumCard symbol="NG" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the comparison, gauge, and tested-not-crowned context when the ship gate passes", () => {
    useVolPremiumMock.mockReturnValue({ data: SUPPORTED });
    render(<VolPremiumCard symbol="CL" />);
    expect(screen.getByText("Vol vs Market")).toBeInTheDocument();
    expect(screen.getByText("31.0%")).toBeInTheDocument(); // ours
    expect(screen.getByText("36.0%")).toBeInTheDocument(); // market
    expect(screen.getByText(/22th pct|22nd pct|22/)).toBeInTheDocument();
    expect(
      screen.getByText(/Timing is tested, not crowned/),
    ).toBeInTheDocument();
    // No signal chip words — position, not pronouncement.
    expect(screen.queryByText(/RICH|CHEAP/)).toBeNull();
  });

  it("labels a pair that failed the timing test (gold)", () => {
    useVolPremiumMock.mockReturnValue({
      data: { ...SUPPORTED, timing_tested: false },
    });
    render(<VolPremiumCard symbol="GC" />);
    expect(screen.getByText(/FAILED the timing test/)).toBeInTheDocument();
  });

  it("renders the honest note instead of the comparison when the live ship gate fails", () => {
    useVolPremiumMock.mockReturnValue({
      data: { ...SUPPORTED, ship_gate: false },
    });
    render(<VolPremiumCard symbol="CL" />);
    expect(screen.getByText(/ship gate is not met/)).toBeInTheDocument();
    expect(screen.queryByText("31.0%")).toBeNull(); // no numbers shown
  });
});
