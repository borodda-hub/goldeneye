import type { ValidationLedgerRow } from "@/lib/api";
import { render, screen } from "@testing-library/react";
import { ValidationLedgerTable } from "../ValidationLedgerTable";
import { VerdictTag } from "../VerdictTag";

const ROW = (over: Partial<ValidationLedgerRow>): ValidationLedgerRow => ({
  key: "k",
  claim: "A claim",
  verdict: "edge",
  provenance: "real-OOS",
  summary: "A summary.",
  evidence: "harness · n=1",
  rerun: null,
  gate_ref: "docs/PLAN.md",
  updated: "2026-07-25",
  ...over,
});

describe("VerdictTag", () => {
  it("maps edge to the up-family badge", () => {
    const { container } = render(<VerdictTag verdict="edge" />);
    expect(screen.getByText("edge · real-oos")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-up");
  });

  it("renders no_edge at full weight — failures are first-class", () => {
    const { container } = render(<VerdictTag verdict="no_edge" />);
    expect(screen.getByText("no edge · tested")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-down");
  });

  it("maps collecting to the cyan archive badge", () => {
    const { container } = render(<VerdictTag verdict="collecting" />);
    expect(container.firstChild).toHaveClass("text-cyan");
  });
});

describe("ValidationLedgerTable", () => {
  it("renders claims, summaries, provenance, and the drift-lock footnote", () => {
    render(
      <ValidationLedgerTable
        rows={[
          ROW({ key: "a", claim: "Range band calibrated" }),
          ROW({
            key: "b",
            claim: "Directional edge",
            verdict: "no_edge",
            summary: "Tested on real data; the claim is retired.",
          }),
        ]}
      />,
    );
    expect(screen.getByText("Range band calibrated")).toBeInTheDocument();
    expect(screen.getByText("Directional edge")).toBeInTheDocument();
    expect(
      screen.getByText("Tested on real data; the claim is retired."),
    ).toBeInTheDocument();
    // The self-verification promise is part of the content contract.
    expect(screen.getByText(/docs\/MODEL_DILIGENCE\.md/)).toBeInTheDocument();
    expect(screen.getByText(/not advice/)).toBeInTheDocument();
  });
});
