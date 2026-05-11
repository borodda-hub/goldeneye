import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { TemplateGallery } from "../TemplateGallery";

const templates = [
  {
    id: "cold_snap_northeast",
    name: "Cold Snap — Northeast 10 Days",
    description: "Sustained Arctic air mass.",
    instrument: "NG",
    shocks: [
      {
        type: "weather" as const,
        region: "northeast",
        delta_temp_f: -12,
        days: 10,
      },
      {
        type: "weather" as const,
        region: "midwest",
        delta_temp_f: -6,
        days: 7,
      },
    ],
  },
  {
    id: "lng_export_disruption",
    name: "LNG Export Disruption",
    description: "Terminal offline.",
    instrument: "NG",
    shocks: [
      { type: "lng_export" as const, delta_bcfd: -2.1, days: 14 },
    ],
  },
];

describe("TemplateGallery", () => {
  it("renders all templates", () => {
    render(<TemplateGallery templates={templates} onSelect={() => {}} />);
    expect(screen.getByText(/Cold Snap/)).toBeInTheDocument();
    expect(screen.getByText(/LNG Export Disruption/)).toBeInTheDocument();
  });

  it("renders shock summary", () => {
    render(<TemplateGallery templates={templates} onSelect={() => {}} />);
    expect(screen.getByText(/2× weather/)).toBeInTheDocument();
  });

  it("calls onSelect with template when clicked", () => {
    const onSelect = vi.fn();
    render(<TemplateGallery templates={templates} onSelect={onSelect} />);
    fireEvent.click(screen.getByText(/Cold Snap/));
    expect(onSelect).toHaveBeenCalledWith(templates[0]);
  });

  it("marks the selected template", () => {
    render(
      <TemplateGallery
        templates={templates}
        onSelect={() => {}}
        selectedId="cold_snap_northeast"
      />,
    );
    expect(screen.getByText(/loaded/i)).toBeInTheDocument();
  });

  it("shows empty state when no templates", () => {
    render(<TemplateGallery templates={[]} onSelect={() => {}} />);
    expect(screen.getByText(/No scenario templates/)).toBeInTheDocument();
  });
});
