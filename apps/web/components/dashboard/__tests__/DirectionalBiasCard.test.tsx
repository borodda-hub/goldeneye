import type {
  DirectionalBias,
  SafetyEnvelope,
} from "@/app/(app)/dashboard/types";
import { fireEvent, render, screen } from "@testing-library/react";
import { DirectionalBiasCard } from "../DirectionalBiasCard";

const bias: DirectionalBias = {
  direction: "bullish",
  confidence: "high",
};

const safety: SafetyEnvelope = {
  confidence: "high",
  caveats: ["Model outputs are statistical inferences only."],
  as_of: "2026-05-10T12:00:00",
  disclaimer: "For research purposes only.",
};

const aiSummary = "Natural gas prices trending higher on supply constraints.";

describe("DirectionalBiasCard", () => {
  it("renders Directional Bias label", () => {
    render(
      <DirectionalBiasCard bias={bias} aiSummary={aiSummary} safety={safety} />,
    );
    expect(screen.getByText(/directional bias/i)).toBeInTheDocument();
  });

  it("renders DirectionChip with correct direction", () => {
    render(
      <DirectionalBiasCard bias={bias} aiSummary={aiSummary} safety={safety} />,
    );
    expect(screen.getByText("Bullish")).toBeInTheDocument();
  });

  it("renders ai_summary text", () => {
    render(
      <DirectionalBiasCard bias={bias} aiSummary={aiSummary} safety={safety} />,
    );
    expect(screen.getByText(aiSummary)).toBeInTheDocument();
  });

  it("SafetyEnvelopeNote is present, collapsed by default, and expandable", () => {
    // Phase U1: the envelope starts collapsed (the card's fixed height goes
    // to the narrative, which scrolls instead of spilling); the caveats stay
    // one click away.
    render(
      <DirectionalBiasCard bias={bias} aiSummary={aiSummary} safety={safety} />,
    );
    expect(screen.queryByText(/statistical inferences/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /as of/i }));
    expect(screen.getByText(/statistical inferences/i)).toBeInTheDocument();
  });
});
