import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ScenarioHistoryList } from "../ScenarioHistoryList";

const runs = [
  {
    run_id: "abc-123",
    created_at: "2026-05-10T14:30:00Z",
    name: "Cold Snap — Northeast",
    instrument_id: "ng-id",
  },
  {
    run_id: "def-456",
    created_at: "2026-05-09T18:00:00Z",
    name: "LNG Export Disruption",
    instrument_id: "ng-id",
  },
];

describe("ScenarioHistoryList", () => {
  it("renders all runs", () => {
    render(<ScenarioHistoryList runs={runs} />);
    expect(screen.getByText("Cold Snap — Northeast")).toBeInTheDocument();
    expect(screen.getByText("LNG Export Disruption")).toBeInTheDocument();
  });

  it("renders formatted timestamps", () => {
    render(<ScenarioHistoryList runs={runs} />);
    expect(screen.getByText("2026-05-10 14:30")).toBeInTheDocument();
  });

  it("calls onSelect with run_id when clicked", () => {
    const onSelect = vi.fn();
    render(<ScenarioHistoryList runs={runs} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Cold Snap — Northeast"));
    expect(onSelect).toHaveBeenCalledWith("abc-123");
  });

  it("shows empty state when no runs", () => {
    render(<ScenarioHistoryList runs={[]} />);
    expect(screen.getByText(/No scenario runs/)).toBeInTheDocument();
  });
});
