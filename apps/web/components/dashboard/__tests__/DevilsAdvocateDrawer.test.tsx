import type { ThesisDevilsAdvocate } from "@/lib/api";
import { render, screen } from "@testing-library/react";
import { DevilsAdvocateDrawer } from "../DevilsAdvocateDrawer";

const review: ThesisDevilsAdvocate = {
  counter_thesis: "The deficit may already be priced into the forward curve.",
  premortem: ["Production rebounds faster than expected"],
  invalidation_signals: ["Smaller EIA storage print Thursday"],
  safety: {
    confidence: "medium",
    caveats: ["A probe, not a verdict."],
    as_of: "2026-06-06T12:00:00Z",
    disclaimer: "Goldeneye is a research tool.",
  },
};

describe("DevilsAdvocateDrawer", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <DevilsAdvocateDrawer
        open={false}
        loading={false}
        error={null}
        review={review}
        onClose={() => {}}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows loading state", () => {
    render(
      <DevilsAdvocateDrawer
        open
        loading
        error={null}
        review={null}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText(/Arguing the other side/)).toBeInTheDocument();
  });

  it("renders the counter-case, pre-mortem, and invalidation signals", () => {
    render(
      <DevilsAdvocateDrawer
        open
        loading={false}
        error={null}
        review={review}
        onClose={() => {}}
      />,
    );
    expect(
      screen.getByText(/deficit may already be priced/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Production rebounds faster than expected"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Smaller EIA storage print Thursday"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Goldeneye is a research tool/),
    ).toBeInTheDocument();
  });

  it("shows the error state", () => {
    render(
      <DevilsAdvocateDrawer
        open
        loading={false}
        error="boom"
        review={null}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText("boom")).toBeInTheDocument();
  });
});
