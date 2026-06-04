import { render, screen } from "@testing-library/react";
import { DISCLAIMER } from "../../lib/strings";
import { DisclaimerFooter } from "../DisclaimerFooter";

describe("DisclaimerFooter", () => {
  it("contains the full disclaimer string", () => {
    render(<DisclaimerFooter />);
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
  });

  it("renders as a footer element", () => {
    const { container } = render(<DisclaimerFooter />);
    expect(container.querySelector("footer")).toBeInTheDocument();
  });
});
