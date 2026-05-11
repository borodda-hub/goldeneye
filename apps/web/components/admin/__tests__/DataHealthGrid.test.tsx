import { render, screen } from "@testing-library/react";
import { DataHealthGrid } from "../DataHealthGrid";

const adapters = [
  {
    name: "market.mock",
    status: "ok" as const,
    last_success: "2026-05-10T14:30:00Z",
    lag_minutes: 2.0,
    rows_ingested: 1200,
    error: null,
    expected_cadence_minutes: 5,
  },
  {
    name: "energy.eia.storage",
    status: "degraded" as const,
    last_success: "2026-05-08T15:00:00Z",
    lag_minutes: 4200.0,
    rows_ingested: 1,
    error: null,
    expected_cadence_minutes: 10080,
  },
  {
    name: "weather.nws",
    status: "down" as const,
    last_success: null,
    lag_minutes: null,
    rows_ingested: null,
    error: "connection refused",
    expected_cadence_minutes: 360,
  },
];

describe("DataHealthGrid", () => {
  it("renders all adapter rows", () => {
    render(<DataHealthGrid adapters={adapters} />);
    expect(screen.getByText("market.mock")).toBeInTheDocument();
    expect(screen.getByText("energy.eia.storage")).toBeInTheDocument();
    expect(screen.getByText("weather.nws")).toBeInTheDocument();
  });

  it("renders status pills for each state", () => {
    render(<DataHealthGrid adapters={adapters} />);
    expect(screen.getByText("ok")).toBeInTheDocument();
    expect(screen.getByText("degraded")).toBeInTheDocument();
    expect(screen.getByText("down")).toBeInTheDocument();
  });

  it("formats lag in minutes/hours/days", () => {
    render(<DataHealthGrid adapters={adapters} />);
    expect(screen.getByText("2m")).toBeInTheDocument();
    // 4200 minutes ≈ 2.9 days
    expect(screen.getByText(/^2\.9d$/)).toBeInTheDocument();
  });

  it("renders dash for null last_success", () => {
    render(<DataHealthGrid adapters={adapters} />);
    // weather.nws has null last_success
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("shows empty state when no adapters", () => {
    render(<DataHealthGrid adapters={[]} />);
    expect(screen.getByText(/No adapter runs/)).toBeInTheDocument();
  });
});
