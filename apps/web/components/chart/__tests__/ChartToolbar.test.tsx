import { fireEvent, render, screen } from "@testing-library/react";
import { ChartToolbar } from "../ChartToolbar";

const defaultProps = {
  resolution: "1d" as const,
  onResolutionChange: vi.fn(),
  indicatorCount: 0,
  onOpenIndicators: vi.fn(),
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
});
