import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

const useModelCalibrationMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useModelCalibration: (...args: unknown[]) => useModelCalibrationMock(...args),
}));
vi.mock("@/components/HelpTip", () => ({ HelpTip: () => null }));

import { ModelCalibrationCard } from "../ModelCalibrationCard";

const overconfident = {
  name: "moving_average_directional",
  brier: 0.34,
  hit_rate: 0.45,
  n: 242,
  buckets: [
    { confidence: "high", claimed_prob: 0.75, actual_rate: 0.43, n: 233 },
  ],
  by_regime: { crisis: { brier: 0.5, hit_rate: 0.2, n: 10 } },
};

describe("ModelCalibrationCard", () => {
  beforeEach(() => useModelCalibrationMock.mockReset());

  it("renders per-model Brier and flags overconfidence", () => {
    useModelCalibrationMock.mockReturnValue({
      data: { models: [overconfident], confidence_prob: {} },
      isLoading: false,
    });
    render(<ModelCalibrationCard symbol="NG" />);
    expect(screen.getByText("moving_average_directional")).toBeInTheDocument();
    expect(screen.getByText("0.340")).toBeInTheDocument();
    // claimed 0.75 but actual 0.43 → overconfident
    expect(screen.getByText("overconfident")).toBeInTheDocument();
    expect(screen.getByText("75%→43%")).toBeInTheDocument();
  });

  it("shows empty state when there are no models", () => {
    useModelCalibrationMock.mockReturnValue({
      data: { models: [], confidence_prob: {} },
      isLoading: false,
    });
    render(<ModelCalibrationCard symbol="NG" />);
    expect(screen.getByText(/No backtest forecasts yet/)).toBeInTheDocument();
  });

  it("toggles the by-regime view", () => {
    useModelCalibrationMock.mockReturnValue({
      data: { models: [overconfident], confidence_prob: {} },
      isLoading: false,
    });
    render(<ModelCalibrationCard symbol="NG" />);
    const toggle = screen.getByRole("button", { name: /By regime/i });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
  });
});
