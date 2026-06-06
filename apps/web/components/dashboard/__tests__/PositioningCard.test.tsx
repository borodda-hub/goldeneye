import type { PositioningResponse } from "@/lib/api";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const usePositioningMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  usePositioning: (...args: unknown[]) => usePositioningMock(...args),
}));

import { PositioningCard } from "../PositioningCard";

function available(): PositioningResponse {
  return {
    symbol: "NG",
    available: true,
    report_date: "2026-05-05",
    release_date: "2026-05-08",
    managed_money_net: 16594,
    managed_money_long: 159956,
    managed_money_short: 143362,
    mm_net_delta: -9484,
    open_interest_total: 1378398,
    source: "CFTC_PRE",
  };
}

function unavailable(): PositioningResponse {
  return {
    symbol: "ES",
    available: false,
    report_date: null,
    release_date: null,
    managed_money_net: null,
    managed_money_long: null,
    managed_money_short: null,
    mm_net_delta: null,
    open_interest_total: null,
    source: null,
  };
}

beforeEach(() => usePositioningMock.mockReset());

describe("PositioningCard", () => {
  it("renders managed-money net and open interest", () => {
    usePositioningMock.mockReturnValue({ data: available(), isLoading: false });
    render(<PositioningCard symbol="NG" />);
    expect(screen.getByText("+16,594")).toBeInTheDocument();
    expect(screen.getByText(/1,378,398/)).toBeInTheDocument();
  });

  it("renders the unavailable empty state", () => {
    usePositioningMock.mockReturnValue({
      data: unavailable(),
      isLoading: false,
    });
    render(<PositioningCard symbol="ES" />);
    expect(
      screen.getByText("No CFTC positioning for this instrument."),
    ).toBeInTheDocument();
  });

  it("renders a loading state", () => {
    usePositioningMock.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<PositioningCard symbol="NG" />);
    expect(container.querySelector(".skeleton")).toBeInTheDocument();
  });
});
