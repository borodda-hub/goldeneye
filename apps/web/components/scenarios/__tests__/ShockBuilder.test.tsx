import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ShockBuilder } from "../ShockBuilder";
import type { Shock } from "@/app/(app)/scenarios/types";

describe("ShockBuilder", () => {
  it("renders empty state with no shocks", () => {
    render(<ShockBuilder shocks={[]} onChange={() => {}} />);
    expect(screen.getByText(/No shocks/)).toBeInTheDocument();
  });

  it("renders a weather shock", () => {
    const shocks: Shock[] = [
      { type: "weather", region: "northeast", delta_temp_f: -8, days: 10 },
    ];
    render(<ShockBuilder shocks={shocks} onChange={() => {}} />);
    expect(screen.getByDisplayValue("northeast")).toBeInTheDocument();
    expect(screen.getByDisplayValue("-8")).toBeInTheDocument();
  });

  it("renders an lng_export shock", () => {
    const shocks: Shock[] = [
      { type: "lng_export", delta_bcfd: -1.5, days: 14 },
    ];
    render(<ShockBuilder shocks={shocks} onChange={() => {}} />);
    expect(screen.getByDisplayValue("-1.5")).toBeInTheDocument();
    expect(screen.getByDisplayValue("14")).toBeInTheDocument();
  });

  it("calls onChange when adding a shock", () => {
    const onChange = vi.fn();
    render(<ShockBuilder shocks={[]} onChange={onChange} />);
    fireEvent.click(screen.getByText(/\+ Add/));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0] as Shock[];
    expect(next).toHaveLength(1);
    expect(next[0].type).toBe("weather");
  });

  it("calls onChange when removing a shock", () => {
    const onChange = vi.fn();
    const shocks: Shock[] = [
      { type: "production", delta_bcfd: -2, days: 7 },
    ];
    render(<ShockBuilder shocks={shocks} onChange={onChange} />);
    fireEvent.click(screen.getByText(/Remove/i));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("shows shocks count", () => {
    const shocks: Shock[] = [
      { type: "storage", delta_bcf: -20, days: 7 },
      { type: "weather", region: "south", delta_temp_f: 5, days: 3 },
    ];
    render(<ShockBuilder shocks={shocks} onChange={() => {}} />);
    expect(screen.getByText(/2 \/ 10/)).toBeInTheDocument();
  });
});
