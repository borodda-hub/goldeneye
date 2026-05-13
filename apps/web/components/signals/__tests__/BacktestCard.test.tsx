import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { BacktestCard } from "../BacktestCard";

const useBacktestSummaryMock = vi.fn();
const mutateMock = vi.fn();
const useRunBacktestMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useBacktestSummary: (...args: unknown[]) => useBacktestSummaryMock(...args),
  useRunBacktest: (...args: unknown[]) => useRunBacktestMock(...args),
}));

function _model(name: string, overrides: Record<string, unknown> = {}) {
  return {
    name,
    n: 91,
    scored: 86,
    hits: 46,
    misses: 35,
    indeterminate: 5,
    pending: 0,
    neutral: 0,
    hit_rate: 0.5349,
    last_generated_at: "2026-05-12T23:59:59",
    from_date: "2026-02-11",
    to_date: "2026-05-12",
    ...overrides,
  };
}

beforeEach(() => {
  useBacktestSummaryMock.mockReset();
  mutateMock.mockReset();
  useRunBacktestMock.mockReset();
  useRunBacktestMock.mockReturnValue({
    mutate: mutateMock,
    isPending: false,
    variables: undefined,
  });
});

describe("BacktestCard", () => {
  it("renders loading state", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    render(<BacktestCard />);
    expect(screen.getByText(/Loading backtest summary/)).toBeInTheDocument();
  });

  it("renders error state", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(<BacktestCard />);
    expect(screen.getByText(/Summary unavailable/)).toBeInTheDocument();
  });

  it("renders empty state when no models persisted", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: { models: [], horizon: "1d", symbol: "NG" },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    expect(screen.getByText(/No backtest rows persisted yet/)).toBeInTheDocument();
  });

  it("renders all four model rows in stable order", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [
          _model("xgboost_placeholder", { hit_rate: 0.5349 }),
          _model("moving_average_directional", { hit_rate: 0.4419 }),
          _model("volatility_regime", { hit_rate: 0.5676, scored: 37 }),
          _model("prophet_trend", { scored: 0, hit_rate: 0.0 }),
        ],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    expect(screen.getByText("SMA Cross")).toBeInTheDocument();
    expect(screen.getByText("Prophet Trend")).toBeInTheDocument();
    expect(screen.getByText("Vol Regime")).toBeInTheDocument();
    expect(screen.getByText("XGBoost")).toBeInTheDocument();
  });

  it("displays hit-rate percentages with one decimal", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [_model("moving_average_directional", { hit_rate: 0.4419 })],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    expect(screen.getByText("44.2%")).toBeInTheDocument();
  });

  it("shows empty-state message for a model with zero scored rows", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [_model("prophet_trend", { scored: 0, hit_rate: 0.0 })],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    expect(
      screen.getByText(/No scored forecasts yet — model returned only neutral/),
    ).toBeInTheDocument();
  });

  it("fires the run mutation with the right model name on Re-run click", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [_model("xgboost_placeholder")],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    const button = screen.getByRole("button", { name: /Re-run backtest for XGBoost/i });
    fireEvent.click(button);
    expect(mutateMock).toHaveBeenCalledWith("xgboost_placeholder");
  });

  it("disables the running model's button while its mutation is pending", () => {
    useRunBacktestMock.mockReturnValue({
      mutate: mutateMock,
      isPending: true,
      variables: "moving_average_directional",
    });
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [
          _model("moving_average_directional"),
          _model("xgboost_placeholder"),
        ],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    const buttons = screen.getAllByRole("button");
    const maButton = buttons.find((b) =>
      b.getAttribute("aria-label")?.includes("SMA Cross"),
    );
    const xgbButton = buttons.find((b) =>
      b.getAttribute("aria-label")?.includes("XGBoost"),
    );
    expect(maButton).toBeDisabled();
    expect(maButton?.textContent).toMatch(/running/);
    // Only the running model's button is disabled — others stay clickable.
    expect(xgbButton).not.toBeDisabled();
  });

  it("renders the date range derived from the widest model window", () => {
    useBacktestSummaryMock.mockReturnValue({
      data: {
        models: [
          _model("moving_average_directional", {
            from_date: "2026-02-11",
            to_date: "2026-05-12",
          }),
          _model("xgboost_placeholder", {
            from_date: "2026-01-01",
            to_date: "2026-04-30",
          }),
        ],
        horizon: "1d",
        symbol: "NG",
      },
      isLoading: false,
      isError: false,
    });
    render(<BacktestCard />);
    expect(screen.getByText(/2026-01-01.*2026-05-12/)).toBeInTheDocument();
  });
});
