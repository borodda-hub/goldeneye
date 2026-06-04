import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const makeRow = (outcome: string, realized_pct: number | null = 0.018) => ({
  rows: [
    {
      id: "1",
      generated_at: "2026-05-09T20:00:00Z",
      horizon_end: "2026-05-10T20:00:00Z",
      model_name: "moving_average_directional",
      horizon: "1d",
      direction: "bullish",
      confidence: "high",
      expected_pct: 0.012,
      vol_regime: "elevated",
      outcome,
      realized_pct,
      delta_from_expected_pct:
        realized_pct !== null ? realized_pct - 0.012 : null,
      scored_at: "2026-05-10T20:00:00Z",
    },
  ],
});

vi.mock("@/lib/queries", () => ({
  useSignalHistory: vi.fn(() => ({
    data: makeRow("hit"),
    isLoading: false,
  })),
}));

import { useSignalHistory } from "@/lib/queries";
import { HistoryTable } from "../HistoryTable";

describe("HistoryTable", () => {
  it("renders hit outcome glyph", () => {
    render(<HistoryTable />);
    expect(screen.getByText("▲")).toBeInTheDocument();
  });

  it("renders expected_pct", () => {
    render(<HistoryTable />);
    expect(screen.getByText("+1.20%")).toBeInTheDocument();
  });

  it("renders realized_pct", () => {
    render(<HistoryTable />);
    expect(screen.getByText("+1.80%")).toBeInTheDocument();
  });

  it("renders model name", () => {
    render(<HistoryTable />);
    expect(screen.getByText(/moving average/)).toBeInTheDocument();
  });

  it("shows empty state when no rows", () => {
    vi.mocked(useSignalHistory).mockReturnValueOnce({
      data: { rows: [] } as any,
      isLoading: false,
    } as any);
    render(<HistoryTable />);
    expect(screen.getByText(/No scored forecasts/)).toBeInTheDocument();
  });
});

describe("HistoryTable outcome glyphs", () => {
  const cases: Array<[string, string, number | null]> = [
    ["miss", "▼", -0.005],
    ["indeterminate", "◇", 0.001],
    ["neutral", "—", 0.01],
    ["pending", "···", null],
  ];

  it.each(cases)("renders %s as %s", (outcome, glyph, realized_pct) => {
    vi.mocked(useSignalHistory).mockReturnValueOnce({
      data: makeRow(outcome, realized_pct),
      isLoading: false,
    } as any);
    render(<HistoryTable />);
    expect(screen.getByText(glyph)).toBeInTheDocument();
  });
});
