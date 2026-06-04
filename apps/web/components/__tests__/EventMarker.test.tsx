import { render, screen } from "@testing-library/react";
import { EventMarker } from "../EventMarker";

const event = {
  headline: "EIA reports larger-than-expected storage draw",
  category: "storage",
  impact_score: 0.72,
  published_at: "2026-05-08T14:30:00",
};

describe("EventMarker", () => {
  it("shows the headline text", () => {
    render(<EventMarker event={event} />);
    expect(screen.getByText(/storage draw/i)).toBeInTheDocument();
  });

  it("shows the category", () => {
    render(<EventMarker event={event} />);
    expect(screen.getByText(/storage/i)).toBeInTheDocument();
  });
});
