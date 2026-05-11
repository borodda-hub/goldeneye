import { render, screen, fireEvent } from "@testing-library/react";
import { ChartToolbar } from "../ChartToolbar";

const defaultProps = {
  resolution: "1d" as const,
  onResolutionChange: vi.fn(),
  showSMA20: true,
  showEMA50: false,
  onToggleSMA20: vi.fn(),
  onToggleEMA50: vi.fn(),
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
      <ChartToolbar {...defaultProps} onResolutionChange={onResolutionChange} />,
    );
    fireEvent.click(screen.getByText("1h"));
    expect(onResolutionChange).toHaveBeenCalledWith("1h");
  });

  it("overlay toggles are visible", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByText("SMA 20")).toBeInTheDocument();
    expect(screen.getByText("EMA 50")).toBeInTheDocument();
  });

  it("contract code is displayed", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByText("NGF26")).toBeInTheDocument();
  });
});
