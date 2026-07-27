import { fireEvent, render, screen } from "@testing-library/react";
import { ExplanationPanel } from "../ExplanationPanel";

const mockSafety = {
  confidence: "medium",
  caveats: ["Model outputs are statistical inferences only."],
  as_of: "2026-05-10T20:00:00Z",
  disclaimer: "Goldeneye is a research terminal.",
};

describe("ExplanationPanel", () => {
  it("renders explanation text", () => {
    render(
      <ExplanationPanel
        explanation="This suggests a moderately bullish setup."
        safety={mockSafety}
      />,
    );
    expect(screen.getByText(/moderately bullish/)).toBeInTheDocument();
  });

  it("renders fallback when explanation is null", () => {
    render(<ExplanationPanel explanation={null} safety={mockSafety} />);
    expect(screen.getByText(/Explanation unavailable/)).toBeInTheDocument();
  });

  it("SafetyEnvelopeNote is collapsed by default and expands to show caveats", () => {
    // Phase U3: the envelope starts collapsed (the panel's height goes to
    // the narrative, which scrolls in-card); caveats are one click away.
    render(<ExplanationPanel explanation="Some text." safety={mockSafety} />);
    expect(
      screen.queryByText(/Model outputs are statistical inferences/),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /as of/i }));
    expect(
      screen.getByText(/Model outputs are statistical inferences/),
    ).toBeInTheDocument();
  });

  it("renders disclaimer text when expanded", () => {
    render(<ExplanationPanel explanation="Some text." safety={mockSafety} />);
    fireEvent.click(screen.getByRole("button", { name: /as of/i }));
    expect(
      screen.getByText(/Goldeneye is a research terminal/),
    ).toBeInTheDocument();
  });
});
