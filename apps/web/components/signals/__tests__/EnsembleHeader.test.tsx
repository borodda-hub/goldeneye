import { render, screen } from "@testing-library/react";
import { EnsembleHeader } from "../EnsembleHeader";

const base = {
  direction: "bullish" as const,
  confidence: "medium" as const,
  vol_regime: "elevated",
  expected_pct: 0.018,
  range: { low_pct: -0.012, high_pct: 0.045 },
  agreement: {
    bullish: 3,
    bearish: 0,
    neutral: 1,
    total: 4,
    input_diversity: "high" as const,
  },
  confidence_rationale: [
    "3 of 4 models agree on bullish direction.",
    "Mixed price + fundamental signals (high input diversity).",
  ],
  caveats: [],
};

describe("EnsembleHeader", () => {
  it("renders direction chip", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText("Bullish")).toBeInTheDocument();
  });

  it("renders expected pct", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText(/\+1\.80%/)).toBeInTheDocument();
  });

  it("renders confidence rationale", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText(/3 of 4 models agree/)).toBeInTheDocument();
  });

  it("renders agreement counts", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText(/3 bull/)).toBeInTheDocument();
  });

  it("renders caveats when present", () => {
    const withCaveat = {
      ...base,
      caveats: ["Models disagree at low volatility; no clear directional signal."],
    };
    render(<EnsembleHeader ensemble={withCaveat} />);
    expect(screen.getByText(/Models disagree/)).toBeInTheDocument();
  });

  it("shows fallback when expected_pct is null", () => {
    render(<EnsembleHeader ensemble={{ ...base, expected_pct: null, range: null }} />);
    expect(screen.getByText(/no range/)).toBeInTheDocument();
  });

  it("renders vol regime label", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText("elevated")).toBeInTheDocument();
  });

  it("renders input diversity tag", () => {
    render(<EnsembleHeader ensemble={base} />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });
});
