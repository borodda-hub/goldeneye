import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

vi.mock("@/lib/api", () => ({
  acknowledgeAlert: vi.fn(),
}));

import { AlertsList } from "../AlertsList";

const alerts = [
  {
    id: "1",
    created_at: "2026-05-10T14:30:00Z",
    kind: "adapter.degraded",
    severity: "warning",
    payload: {},
    read: false,
    acknowledged: false,
  },
  {
    id: "2",
    created_at: "2026-05-09T18:00:00Z",
    kind: "forecast.stale",
    severity: "info",
    payload: {},
    read: true,
    acknowledged: true,
  },
];

describe("AlertsList", () => {
  it("renders alert kinds", () => {
    render(<AlertsList alerts={alerts} />);
    expect(screen.getByText("adapter.degraded")).toBeInTheDocument();
    expect(screen.getByText("forecast.stale")).toBeInTheDocument();
  });

  it("renders Ack button only for unacknowledged alerts", () => {
    render(<AlertsList alerts={alerts} />);
    expect(screen.getByText("Ack")).toBeInTheDocument();
    expect(screen.getByText("acked")).toBeInTheDocument();
  });

  it("renders severity labels", () => {
    render(<AlertsList alerts={alerts} />);
    expect(screen.getByText("warning")).toBeInTheDocument();
    expect(screen.getByText("info")).toBeInTheDocument();
  });

  it("shows empty state when no alerts", () => {
    render(<AlertsList alerts={[]} />);
    expect(screen.getByText(/No active alerts/)).toBeInTheDocument();
  });
});
