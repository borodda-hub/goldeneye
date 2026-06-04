import type { RecentEvent } from "@/app/(app)/dashboard/types";
import { render, screen } from "@testing-library/react";
import { RecentEventsList } from "../RecentEventsList";

const events: RecentEvent[] = [
  {
    id: "1",
    published_at: "2026-05-10T10:00:00Z",
    headline: "EIA storage report: build of 82 Bcf",
    category: "storage",
    impact_score: 0.75,
  },
  {
    id: "2",
    published_at: "2026-05-10T08:00:00Z",
    headline: "Cold snap forecast for Midwest",
    category: "weather",
    impact_score: 0.6,
  },
];

describe("RecentEventsList", () => {
  it("renders Recent Events label", () => {
    render(<RecentEventsList events={events} />);
    expect(screen.getByText(/recent events/i)).toBeInTheDocument();
  });

  it("renders the correct number of event rows", () => {
    render(<RecentEventsList events={events} />);
    expect(screen.getByText(/EIA storage report/)).toBeInTheDocument();
    expect(screen.getByText(/Cold snap forecast/)).toBeInTheDocument();
  });

  it("renders empty state when empty array", () => {
    render(<RecentEventsList events={[]} />);
    expect(screen.getByText("No recent events.")).toBeInTheDocument();
  });
});
