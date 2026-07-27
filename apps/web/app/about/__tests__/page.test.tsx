import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AboutPage from "../page";

/**
 * Truth-discipline locks for the white paper (Phase A4). The page is a static
 * server component, so we lock the parts that carry the honesty contract:
 * the disclaimer, the forbidden-phrase scan, and the section skeleton.
 */

// docs/AI_BEHAVIOR.md §forbidden_phrases — none may appear in page copy.
// ("buy now"/"sell now" are the forbidden forms; "buy"/"sell" alone are not.)
const FORBIDDEN = [
  /guaranteed/i,
  /will profit/i,
  /sure thing/i,
  /risk-free/i,
  /buy now/i,
  /sell now/i,
  /go long/i,
  /go short/i,
  /hot tip/i,
  /moonshot/i,
];

const SECTION_IDS = [
  "positioning",
  "problem",
  "doctrine",
  "forecast-engine",
  "vol-engine",
  "data-layer",
  "decision-intelligence",
  "ai-layer",
  "architecture",
  "results",
  "limitations",
];

describe("AboutPage (white paper)", () => {
  it("carries the §disclaimer string verbatim", () => {
    const { container } = render(<AboutPage />);
    expect(container.textContent).toContain(
      "Goldeneye is a research and decision-support terminal. It does not provide personalized financial advice, does not execute trades against real brokers, and does not guarantee any forecast or scenario. Paper trading is simulated. For research, education, and decision-quality practice only.",
    );
  });

  it("contains no forbidden phrases", () => {
    const { container } = render(<AboutPage />);
    const text = container.textContent ?? "";
    for (const re of FORBIDDEN) {
      expect(text).not.toMatch(re);
    }
  });

  it("renders every contracted section with a deep-linkable id", () => {
    const { container } = render(<AboutPage />);
    for (const id of SECTION_IDS) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
  });

  it("states the honest headline: direction has no edge, ranges are the edge", () => {
    const { container } = render(<AboutPage />);
    const text = container.textContent ?? "";
    expect(text).toMatch(/none earned an edge/i);
    expect(text).toMatch(/labeled views/i);
    expect(text).toMatch(/78–81%/);
  });

  it("links to the live validation ledger and the terminal", () => {
    const { container } = render(<AboutPage />);
    const hrefs = Array.from(container.querySelectorAll("a")).map((a) =>
      a.getAttribute("href"),
    );
    expect(hrefs).toContain("/validation");
    expect(hrefs).toContain("/dashboard");
  });
});
