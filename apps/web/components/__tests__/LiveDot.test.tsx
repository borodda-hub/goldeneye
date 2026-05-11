import { render } from "@testing-library/react";
import { LiveDot } from "../LiveDot";

describe("LiveDot", () => {
	it("has animate-pulse class when connected", () => {
		const { container } = render(<LiveDot connected={true} />);
		expect(container.firstChild).toHaveClass("animate-pulse");
		expect(container.firstChild).toHaveClass("bg-up");
	});

	it("does not have animate-pulse when disconnected", () => {
		const { container } = render(<LiveDot connected={false} />);
		expect(container.firstChild).not.toHaveClass("animate-pulse");
		expect(container.firstChild).toHaveClass("bg-down");
	});

	it("has correct aria-label for connected state", () => {
		const { container } = render(<LiveDot connected={true} />);
		expect(container.firstChild).toHaveAttribute("aria-label", "Connected");
	});

	it("has correct aria-label for disconnected state", () => {
		const { container } = render(<LiveDot connected={false} />);
		expect(container.firstChild).toHaveAttribute("aria-label", "Disconnected");
	});
});
