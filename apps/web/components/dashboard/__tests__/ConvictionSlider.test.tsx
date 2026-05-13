import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ConvictionSlider } from "../ConvictionSlider";

describe("ConvictionSlider", () => {
  it("renders the current value as a percentage", () => {
    render(<ConvictionSlider value={68} onChange={() => {}} />);
    expect(screen.getByText("68%")).toBeInTheDocument();
  });

  it("renders bucket tick marks at 0/25/50/75/100", () => {
    render(<ConvictionSlider value={50} onChange={() => {}} />);
    for (const t of ["0", "25", "50", "75", "100"]) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
  });

  it("calls onChange with the new numeric value when slider moves", () => {
    const onChange = vi.fn();
    render(<ConvictionSlider value={50} onChange={onChange} />);
    fireEvent.change(screen.getByRole("slider"), { target: { value: "80" } });
    expect(onChange).toHaveBeenCalledWith(80);
  });

  it("disables interaction when disabled is true", () => {
    render(<ConvictionSlider value={40} onChange={() => {}} disabled />);
    expect(screen.getByRole("slider")).toBeDisabled();
  });
});
