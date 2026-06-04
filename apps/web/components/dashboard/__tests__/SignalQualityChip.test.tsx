import type { SignalQualityResponse } from "@/lib/api";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useSignalQualityMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useSignalQuality: (...args: unknown[]) => useSignalQualityMock(...args),
}));

import { SignalQualityChip } from "../SignalQualityChip";

function _sample(): SignalQualityResponse {
  return {
    symbol: "NG",
    grade: "B",
    total_score: 78,
    sub_scores: {
      input_diversity: 30,
      model_agreement: 20,
      regime_stability: 15,
      time_to_decision: 13,
    },
    sub_score_max: {
      input_diversity: 30,
      model_agreement: 25,
      regime_stability: 25,
      time_to_decision: 20,
    },
    detail: {
      input_diversity: "high",
      model_agreement_total: 4,
      model_agreement_max: 3,
      regime_stability: "mixed",
      distinct_regimes_14d: 2,
      time_to_decision_bucket: "≤4h",
      minutes_since_freshness_adapter: 120,
    },
  };
}

beforeEach(() => {
  useSignalQualityMock.mockReset();
});

describe("SignalQualityChip", () => {
  it("renders a placeholder while loading", () => {
    useSignalQualityMock.mockReturnValue({ data: undefined, isLoading: true });
    render(<SignalQualityChip />);
    expect(screen.getByText(/SQ: …/)).toBeInTheDocument();
  });

  it("renders the grade letter when data is loaded", () => {
    useSignalQualityMock.mockReturnValue({ data: _sample(), isLoading: false });
    render(<SignalQualityChip />);
    const chip = screen.getByTestId("signal-quality-chip");
    expect(chip).toHaveTextContent("SQ: B");
    expect(chip).toHaveAccessibleName(/Signal Quality B, total 78 out of 100/);
  });

  it("opens the popover when the chip is clicked", () => {
    useSignalQualityMock.mockReturnValue({ data: _sample(), isLoading: false });
    render(<SignalQualityChip />);
    fireEvent.click(screen.getByTestId("signal-quality-chip"));
    expect(
      screen.getByRole("dialog", { name: /Signal Quality breakdown/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Input diversity")).toBeInTheDocument();
    expect(screen.getByText("Model agreement")).toBeInTheDocument();
    expect(screen.getByText("Regime stability")).toBeInTheDocument();
    expect(screen.getByText("Data freshness")).toBeInTheDocument();
  });

  it("renders the popover details derived from the response", () => {
    useSignalQualityMock.mockReturnValue({ data: _sample(), isLoading: false });
    render(<SignalQualityChip />);
    fireEvent.click(screen.getByTestId("signal-quality-chip"));
    expect(screen.getByText(/adapter coverage: high/)).toBeInTheDocument();
    expect(screen.getByText(/3 of 4 models aligned/)).toBeInTheDocument();
    expect(screen.getByText(/mixed \(2 distinct regimes/)).toBeInTheDocument();
    expect(screen.getByText(/latest run 120m ago \(≤4h\)/)).toBeInTheDocument();
  });

  it("handles missing freshness data ('no-data' bucket)", () => {
    const sample = _sample();
    sample.detail.minutes_since_freshness_adapter = null;
    sample.detail.time_to_decision_bucket = "no-data";
    sample.sub_scores.time_to_decision = 0;
    useSignalQualityMock.mockReturnValue({ data: sample, isLoading: false });
    render(<SignalQualityChip />);
    fireEvent.click(screen.getByTestId("signal-quality-chip"));
    expect(screen.getByText(/no recent adapter runs/)).toBeInTheDocument();
  });
});
