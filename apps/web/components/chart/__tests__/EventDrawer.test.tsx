import type { EventMarkerData } from "@/app/(app)/chart/types";
import { fireEvent, render, screen } from "@testing-library/react";
import { EventDrawer } from "../EventDrawer";

const events: EventMarkerData[] = [
  {
    ts: "2026-05-01T10:00:00Z",
    kind: "eia_storage",
    label: "EIA Storage Report",
    delta: 82,
  },
  {
    ts: "2026-05-08T10:00:00Z",
    kind: "weather",
    label: "Cold snap alert",
    delta: -45,
  },
];

describe("EventDrawer", () => {
  it("when closed, shows handle with toggle button", () => {
    const onToggle = vi.fn();
    render(<EventDrawer events={events} open={false} onToggle={onToggle} />);
    expect(screen.getByLabelText("Open events drawer")).toBeInTheDocument();
  });

  it("when open, shows events list header", () => {
    render(<EventDrawer events={events} open={true} onToggle={vi.fn()} />);
    expect(screen.getByText(/^events$/i)).toBeInTheDocument();
  });

  it("toggle button calls onToggle when closed", () => {
    const onToggle = vi.fn();
    render(<EventDrawer events={events} open={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Open events drawer"));
    expect(onToggle).toHaveBeenCalled();
  });

  it("toggle button calls onToggle when open", () => {
    const onToggle = vi.fn();
    render(<EventDrawer events={events} open={true} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Close events drawer"));
    expect(onToggle).toHaveBeenCalled();
  });

  it("shows empty state when events is empty", () => {
    render(<EventDrawer events={[]} open={true} onToggle={vi.fn()} />);
    expect(screen.getByText("No events in range.")).toBeInTheDocument();
  });
});
