import type { FundamentalsResponse } from "@/lib/api";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useFundamentalsMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useFundamentals: (...args: unknown[]) => useFundamentalsMock(...args),
}));

import { FundamentalsCard } from "../FundamentalsCard";

function gas(): FundamentalsResponse {
  return {
    symbol: "NG",
    kind: "gas_storage",
    title: "Working Gas in Storage",
    unit: "Bcf",
    latest: {
      as_of: "2026-05-01",
      level: 1512.1,
      net_change: 2.7,
      surprise: -0.3,
      five_year_avg: 1500.4,
    },
    source: "EIA",
    empty_reason: null,
  };
}

function metalEmpty(): FundamentalsResponse {
  return {
    symbol: "GC",
    kind: "none",
    title: "Fundamentals",
    unit: null,
    latest: null,
    source: null,
    empty_reason: "No EIA inventory report for this asset class",
  };
}

beforeEach(() => useFundamentalsMock.mockReset());

describe("FundamentalsCard", () => {
  it("renders gas storage data", () => {
    useFundamentalsMock.mockReturnValue({ data: gas(), isLoading: false });
    render(<FundamentalsCard symbol="NG" />);
    expect(screen.getByText("Working Gas in Storage")).toBeInTheDocument();
    expect(screen.getByText("1,512.1")).toBeInTheDocument();
    expect(screen.getByText("Bcf")).toBeInTheDocument();
  });

  it("renders the metals empty state", () => {
    useFundamentalsMock.mockReturnValue({
      data: metalEmpty(),
      isLoading: false,
    });
    render(<FundamentalsCard symbol="GC" />);
    expect(
      screen.getByText("No EIA inventory report for this asset class"),
    ).toBeInTheDocument();
  });

  it("renders a loading state", () => {
    useFundamentalsMock.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<FundamentalsCard symbol="NG" />);
    expect(container.querySelector(".skeleton")).toBeInTheDocument();
  });
});
