import { render } from "@testing-library/react";
import { LiveDot } from "../LiveDot";

describe("LiveDot", () => {
	it("has animate-pulse class when connected (live mode default)", () => {
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

	it("renders amber, no pulse, and a delayed aria-label when mode=delayed", () => {
		const { container } = render(<LiveDot connected={true} mode="delayed" />);
		expect(container.firstChild).toHaveClass("bg-conf-medium");
		expect(container.firstChild).not.toHaveClass("animate-pulse");
		expect(container.firstChild).not.toHaveClass("bg-up");
		expect(container.firstChild).toHaveAttribute(
			"aria-label",
			"Connected (delayed feed)",
		);
	});

	it("ignores mode when disconnected — always shows down state", () => {
		const { container } = render(<LiveDot connected={false} mode="delayed" />);
		expect(container.firstChild).toHaveClass("bg-down");
		expect(container.firstChild).toHaveAttribute("aria-label", "Disconnected");
	});
});
