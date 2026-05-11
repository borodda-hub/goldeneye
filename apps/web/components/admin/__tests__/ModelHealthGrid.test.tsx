import { render, screen } from "@testing-library/react";
import { ModelHealthGrid } from "../ModelHealthGrid";

const models = [
  {
    name: "moving_average_directional",
    last_forecast_at: "2026-05-10T20:00:00Z",
    sample_count_7d: 7,
  },
  {
    name: "xgboost_placeholder",
    last_forecast_at: "2026-05-09T20:00:00Z",
    sample_count_7d: 5,
  },
];

describe("ModelHealthGrid", () => {
  it("renders model names", () => {
    render(<ModelHealthGrid models={models} />);
    expect(screen.getByText("moving_average_directional")).toBeInTheDocument();
    expect(screen.getByText("xgboost_placeholder")).toBeInTheDocument();
  });

  it("renders sample counts", () => {
    render(<ModelHealthGrid models={models} />);
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows empty state when no models", () => {
    render(<ModelHealthGrid models={[]} />);
    expect(screen.getByText(/No forecasts in the last 7 days/)).toBeInTheDocument();
  });
});
