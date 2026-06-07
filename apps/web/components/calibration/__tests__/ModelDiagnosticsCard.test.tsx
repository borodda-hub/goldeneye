import { render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

const useModelDiagnosticsMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useModelDiagnostics: () => useModelDiagnosticsMock(),
}));

import { ModelDiagnosticsCard } from "../ModelDiagnosticsCard";

const models = [
  {
    name: "logreg_directional",
    directional_bias: {
      bullish_calls: 80,
      bearish_calls: 169,
      call_skew: 0.32,
      bullish_hit_rate: 0.65,
      bearish_hit_rate: 0.5,
      hit_rate_gap: 0.15,
    },
    brier_decomposition: {
      n: 249,
      base_rate: 0.55,
      reliability: 0.01,
      resolution: 0.0,
      uncertainty: 0.25,
      brier: 0.26,
    },
    regime_accuracy: {
      normal: { hit_rate: 0.6, n: 200 },
      crisis: { hit_rate: 0.3, n: 49 },
    },
    feature_drift: {
      n_early: 120,
      n_late: 129,
      early_top: [{ factor: "momentum_5d", share: 0.5 }],
      late_top: [{ factor: "trend_vs_sma20", share: 0.6 }],
      shifts: [
        {
          factor: "trend_vs_sma20",
          early_share: 0.2,
          late_share: 0.6,
          delta: 0.4,
        },
      ],
    },
  },
];

describe("ModelDiagnosticsCard", () => {
  beforeEach(() => useModelDiagnosticsMock.mockReset());

  it("renders a model with its Brier decomposition + drift", () => {
    useModelDiagnosticsMock.mockReturnValue({
      data: { models, confidence_prob: {} },
      isLoading: false,
    });
    render(<ModelDiagnosticsCard symbol="NG" />);
    expect(screen.getByText("Logistic (trained)")).toBeInTheDocument();
    expect(screen.getByText("0.260")).toBeInTheDocument(); // brier
    expect(screen.getByText(/trend_vs_sma20/)).toBeInTheDocument(); // drift
    expect(screen.getByText(/crisis/)).toBeInTheDocument(); // regime chip
  });

  it("shows empty state when no backtest rows exist", () => {
    useModelDiagnosticsMock.mockReturnValue({
      data: { models: [], confidence_prob: {} },
      isLoading: false,
    });
    render(<ModelDiagnosticsCard symbol="NG" />);
    expect(screen.getByText(/No backtest rows yet/)).toBeInTheDocument();
  });
});
