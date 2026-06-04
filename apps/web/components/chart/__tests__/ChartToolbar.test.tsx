import { fireEvent, render, screen } from "@testing-library/react";
import { ChartToolbar } from "../ChartToolbar";

const defaultProps = {
  resolution: "1d" as const,
  onResolutionChange: vi.fn(),
  chartType: "candlestick" as const,
  onChartTypeChange: vi.fn(),
  range: "2Y" as const,
  onRangeChange: vi.fn(),
  logScale: false,
  onToggleLog: vi.fn(),
  showCurve: false,
  onToggleCurve: vi.fn(),
  showPatterns: false,
  onTogglePatterns: vi.fn(),
  patternCount: 0,
  indicatorCount: 0,
  onOpenIndicators: vi.fn(),
  onClearIndicators: vi.fn(),
  onScreenshot: vi.fn(),
  onFullscreen: vi.fn(),
  contractCode: "NGF26",
};

describe("ChartToolbar", () => {
  it("renders all 5 resolution buttons", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByText("1m")).toBeInTheDocument();
    expect(screen.getByText("5m")).toBeInTheDocument();
    expect(screen.getByText("15m")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("1d")).toBeInTheDocument();
  });

  it("selected resolution has accent styling", () => {
    render(<ChartToolbar {...defaultProps} resolution="1d" />);
    const btn = screen.getByText("1d").closest("button");
    expect(btn?.className).toContain("text-accent");
  });

  it("clicking a different resolution calls onResolutionChange", () => {
    const onResolutionChange = vi.fn();
    render(
      <ChartToolbar
        {...defaultProps}
        onResolutionChange={onResolutionChange}
      />,
    );
    fireEvent.click(screen.getByText("1h"));
    expect(onResolutionChange).toHaveBeenCalledWith("1h");
  });

  it("clicking Indicators opens the picker", () => {
    const onOpenIndicators = vi.fn();
    render(
      <ChartToolbar {...defaultProps} onOpenIndicators={onOpenIndicators} />,
    );
    fireEvent.click(screen.getByLabelText(/open indicators picker/i));
    expect(onOpenIndicators).toHaveBeenCalled();
  });

  it("indicator count is shown when > 0", () => {
    render(<ChartToolbar {...defaultProps} indicatorCount={3} />);
    expect(screen.getByText("(3)")).toBeInTheDocument();
  });

  it("indicator count is hidden when 0", () => {
    render(<ChartToolbar {...defaultProps} indicatorCount={0} />);
    expect(screen.queryByText(/^\(0\)$/)).not.toBeInTheDocument();
  });

  it("contract code is displayed", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByText("NGF26")).toBeInTheDocument();
  });

  it("clear button appears only when indicatorCount > 0", () => {
    const { rerender } = render(
      <ChartToolbar {...defaultProps} indicatorCount={0} />,
    );
    expect(
      screen.queryByLabelText(/clear all indicators/i),
    ).not.toBeInTheDocument();

    rerender(<ChartToolbar {...defaultProps} indicatorCount={3} />);
    expect(screen.getByLabelText(/clear all indicators/i)).toBeInTheDocument();
  });

  it("clicking clear calls onClearIndicators", () => {
    const onClearIndicators = vi.fn();
    render(
      <ChartToolbar
        {...defaultProps}
        indicatorCount={2}
        onClearIndicators={onClearIndicators}
      />,
    );
    fireEvent.click(screen.getByLabelText(/clear all indicators/i));
    expect(onClearIndicators).toHaveBeenCalled();
  });

  it("changing the chart type calls onChartTypeChange", () => {
    const onChartTypeChange = vi.fn();
    render(
      <ChartToolbar {...defaultProps} onChartTypeChange={onChartTypeChange} />,
    );
    fireEvent.change(screen.getByLabelText(/chart type/i), {
      target: { value: "heikin-ashi" },
    });
    expect(onChartTypeChange).toHaveBeenCalledWith("heikin-ashi");
  });

  it("clicking a range preset calls onRangeChange", () => {
    const onRangeChange = vi.fn();
    render(<ChartToolbar {...defaultProps} onRangeChange={onRangeChange} />);
    fireEvent.click(screen.getByText("6M"));
    expect(onRangeChange).toHaveBeenCalledWith("6M");
  });

  it("toggles log scale and curve and exports", () => {
    const onToggleLog = vi.fn();
    const onToggleCurve = vi.fn();
    const onScreenshot = vi.fn();
    const onFullscreen = vi.fn();
    render(
      <ChartToolbar
        {...defaultProps}
        onToggleLog={onToggleLog}
        onToggleCurve={onToggleCurve}
        onScreenshot={onScreenshot}
        onFullscreen={onFullscreen}
      />,
    );
    fireEvent.click(screen.getByText("LOG"));
    fireEvent.click(screen.getByText("Curve"));
    fireEvent.click(screen.getByLabelText(/download chart as png/i));
    fireEvent.click(screen.getByLabelText(/toggle fullscreen/i));
    expect(onToggleLog).toHaveBeenCalled();
    expect(onToggleCurve).toHaveBeenCalled();
    expect(onScreenshot).toHaveBeenCalled();
    expect(onFullscreen).toHaveBeenCalled();
  });

  it("toggles patterns and shows the count when active", () => {
    const onTogglePatterns = vi.fn();
    const { rerender } = render(
      <ChartToolbar {...defaultProps} onTogglePatterns={onTogglePatterns} />,
    );
    fireEvent.click(screen.getByText("Patterns"));
    expect(onTogglePatterns).toHaveBeenCalled();
    // Count shows only when active.
    rerender(
      <ChartToolbar {...defaultProps} showPatterns={true} patternCount={5} />,
    );
    expect(screen.getByText("(5)")).toBeInTheDocument();
  });
});
