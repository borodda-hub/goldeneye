import { render, screen } from "@testing-library/react";
import { DisclaimerFooter } from "../DisclaimerFooter";
import { DISCLAIMER } from "../../lib/strings";

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
