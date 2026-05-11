import { render, screen } from "@testing-library/react";
import { EquityCurveChart } from "../EquityCurveChart";
import type { EquityPoint } from "../../../app/(app)/paper/types";

const upSeries: EquityPoint[] = [
  { date: "2026-04-01", equity: 100000 },
  { date: "2026-04-15", equity: 101500 },
  { date: "2026-05-01", equity: 103200 },
];

const downSeries: EquityPoint[] = [
  { date: "2026-04-01", equity: 100000 },
  { date: "2026-04-15", equity: 98500 },
  { date: "2026-05-01", equity: 97200 },
];

describe("EquityCurveChart", () => {
  it("renders heading", () => {
    render(<EquityCurveChart series={upSeries} />);
    expect(screen.getByText(/Equity Curve/)).toBeInTheDocument();
  });

  it("shows empty state when series is empty", () => {
    render(<EquityCurveChart series={[]} />);
    expect(screen.getByText(/No equity data/)).toBeInTheDocument();
  });

  it("shows last equity in green when up", () => {
    render(<EquityCurveChart series={upSeries} />);
    const label = screen.getByText("$103200");
    expect(label.className).toContain("text-up");
  });

  it("shows last equity in red when down", () => {
    render(<EquityCurveChart series={downSeries} />);
    const label = screen.getByText("$97200");
    expect(label.className).toContain("text-down");
  });

  it("shows starting equity when series is empty", () => {
    render(<EquityCurveChart series={[]} />);
    expect(screen.getByText("$100000")).toBeInTheDocument();
  });
});
