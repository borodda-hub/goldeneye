import { render, screen } from "@testing-library/react";
import { ModelGrid } from "../ModelGrid";

const mockModels = [
  {
    model_name: "moving_average_directional",
    horizon: "1d",
    direction: "bullish" as const,
    confidence: "high" as const,
    expected_pct: 0.012,
    inputs_used: ["closes"],
    range: { low_pct: -0.02, high_pct: 0.04 },
    supporting: [
      { factor: "SMA cross", weight: 0.7, note: "SMA-20 above SMA-50 by 0.8%" },
    ],
    contradicting: [
      { factor: "RSI overbought", weight: 0.3, note: "RSI at 72" },
    ],
  },
];

describe("ModelGrid", () => {
  it("renders model name", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText(/moving average directional/)).toBeInTheDocument();
  });

  it("renders horizon chip", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText("1d")).toBeInTheDocument();
  });

  it("renders supporting factor", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText("SMA cross")).toBeInTheDocument();
  });

  it("renders contradicting factor", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText("RSI overbought")).toBeInTheDocument();
  });

  it("renders inputs_used tag", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText("closes")).toBeInTheDocument();
  });

  it("renders expected pct", () => {
    render(<ModelGrid models={mockModels} />);
    expect(screen.getByText("+1.20%")).toBeInTheDocument();
  });

  it("shows empty state when no models", () => {
    render(<ModelGrid models={[]} />);
    expect(screen.getByText(/No model results/)).toBeInTheDocument();
  });
});
