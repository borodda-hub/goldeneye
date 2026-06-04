import { render, screen } from "@testing-library/react";
import { DirectionChip } from "../DirectionChip";

describe("DirectionChip", () => {
  it("renders Bullish with bg-up-soft class", () => {
    const { container } = render(<DirectionChip direction="bullish" />);
    expect(screen.getByText("Bullish")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-up-soft");
  });

  it("renders Bearish with bg-down-soft class", () => {
    const { container } = render(<DirectionChip direction="bearish" />);
    expect(screen.getByText("Bearish")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-down-soft");
  });

  it("renders Neutral with bg-surface-2 class", () => {
    const { container } = render(<DirectionChip direction="neutral" />);
    expect(screen.getByText("Neutral")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-surface-2");
  });
});
