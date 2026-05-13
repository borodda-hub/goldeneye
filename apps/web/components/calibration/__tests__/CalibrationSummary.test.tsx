import { render, screen } from "@testing-library/react";
import type { CalibrationResponse } from "@/lib/api";
import { CalibrationSummary } from "../CalibrationSummary";

function _data(overrides: Partial<CalibrationResponse> = {}): CalibrationResponse {
  return {
    instrument_code: "NG",
    buckets: [],
    total_entries: 14,
    resolved_entries: 12,
    unresolved_entries: 2,
    summary: "Your 70% theses resolved at 64% (n=12).",
    ...overrides,
  };
}

describe("CalibrationSummary", () => {
  it("renders the summary sentence when present", () => {
    render(<CalibrationSummary data={_data()} />);
    expect(screen.getByText(/Your 70% theses/)).toBeInTheDocument();
    expect(screen.getByText(/64% \(n=12\)/)).toBeInTheDocument();
  });

  it("renders the no-drift fallback copy when summary is null", () => {
    render(
      <CalibrationSummary
        data={_data({ summary: null, total_entries: 4, resolved_entries: 4, unresolved_entries: 0 })}
      />,
    );
    expect(
      screen.getByText(/calibrate within 5 percentage points/),
    ).toBeInTheDocument();
  });

  it("shows sample counts", () => {
    render(<CalibrationSummary data={_data()} />);
    expect(screen.getByText("Total entries")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
    expect(screen.getByText("Resolved")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Unresolved")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
