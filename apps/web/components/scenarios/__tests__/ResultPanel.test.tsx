import { render, screen } from "@testing-library/react";
import { ResultPanel } from "../ResultPanel";

const mockResult = {
  directional_pressure: "bullish" as const,
  confidence: "medium" as const,
  affected_timeframe: "1-2 weeks",
  expected_pct_range: { low: 0.02, high: 0.09 },
  assumptions: [
    "Cold air mass of -12°F persists for 10 days in northeast.",
    "Production headwind of 3.5 Bcf/d for 7 days.",
  ],
  counterarguments: [
    "Weather forecasts beyond 7 days carry significant uncertainty.",
  ],
  data_needed_to_validate: [
    "NWS 6-10 day temp anomaly map.",
    "EIA Weekly Storage Report on Thursday.",
  ],
  narrative:
    "This scenario assumes a sustained cold air mass. The data would shift toward higher heating demand. The directional pressure reads as bullish with moderate confidence. However, the strongest counterargument is uncertainty in extended forecasts. Validating data: NWS maps and EIA weekly report.",
  safety: {
    confidence: "medium",
    caveats: ["Scenario outputs are hypothetical."],
    as_of: "2026-05-11T12:00:00Z",
    disclaimer: "Goldeneye is a research terminal.",
  },
};

describe("ResultPanel", () => {
  it("renders scenario name", () => {
    render(<ResultPanel result={mockResult} name="Test Scenario" />);
    expect(screen.getByText("Test Scenario")).toBeInTheDocument();
  });

  it("renders directional pressure", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText("Bullish")).toBeInTheDocument();
  });

  it("renders timeframe", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText("1-2 weeks")).toBeInTheDocument();
  });

  it("renders expected range", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText(/2\.00% – 9\.00%/)).toBeInTheDocument();
  });

  it("renders assumptions", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText(/Cold air mass/)).toBeInTheDocument();
  });

  it("renders counterarguments", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText(/Weather forecasts/)).toBeInTheDocument();
  });

  it("renders data needed to validate", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText(/NWS 6-10 day/)).toBeInTheDocument();
  });

  it("renders narrative", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.getByText(/This scenario assumes/)).toBeInTheDocument();
  });

  it("renders safety envelope caveats (open by default)", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(
      screen.getByText(/Scenario outputs are hypothetical/),
    ).toBeInTheDocument();
  });

  it("renders fallback narrative when missing", () => {
    render(
      <ResultPanel result={{ ...mockResult, narrative: "" }} name="Test" />,
    );
    expect(screen.getByText(/Narrative unavailable/)).toBeInTheDocument();
  });

  it("does not render the Export PDF link when no runId is provided", () => {
    render(<ResultPanel result={mockResult} name="Test" />);
    expect(screen.queryByTestId("export-pdf-link")).toBeNull();
  });

  it("renders the Export PDF link with the correct download URL when runId is provided", () => {
    const runId = "abc-123-def";
    render(<ResultPanel result={mockResult} name="Test" runId={runId} />);
    const link = screen.getByTestId("export-pdf-link") as HTMLAnchorElement;
    expect(link).toBeInTheDocument();
    expect(link.href).toContain(
      `/v1/scenarios/runs/${encodeURIComponent(runId)}/export.pdf`,
    );
    expect(link.target).toBe("_blank");
    expect(link.rel).toContain("noopener");
  });
});
