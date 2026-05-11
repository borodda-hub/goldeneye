import { render, screen } from "@testing-library/react";
import { ExplanationPanel } from "../ExplanationPanel";

const mockSafety = {
  confidence: "medium",
  caveats: ["Model outputs are statistical inferences only."],
  as_of: "2026-05-10T20:00:00Z",
  disclaimer: "NGTI is a research prototype.",
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

  it("renders SafetyEnvelopeNote open — shows caveats", () => {
    render(
      <ExplanationPanel explanation="Some text." safety={mockSafety} />,
    );
    expect(
      screen.getByText(/Model outputs are statistical inferences/),
    ).toBeInTheDocument();
  });

  it("renders disclaimer text", () => {
    render(<ExplanationPanel explanation="Some text." safety={mockSafety} />);
    expect(screen.getByText(/NGTI is a research prototype/)).toBeInTheDocument();
  });
});
