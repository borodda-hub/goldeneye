import { render } from "@testing-library/react";
import { ConfidenceBar } from "../ConfidenceBar";

function getFilledSegments(container: HTMLElement) {
	return container.querySelectorAll("[data-filled='true']");
}

describe("ConfidenceBar", () => {
	it("fills 1 segment for low", () => {
		const { container } = render(<ConfidenceBar confidence="low" />);
		expect(getFilledSegments(container)).toHaveLength(1);
	});

	it("fills 2 segments for medium", () => {
		const { container } = render(<ConfidenceBar confidence="medium" />);
		expect(getFilledSegments(container)).toHaveLength(2);
	});

	it("fills 3 segments for high", () => {
		const { container } = render(<ConfidenceBar confidence="high" />);
		expect(getFilledSegments(container)).toHaveLength(3);
	});
});
