import { render, screen } from "@testing-library/react";
import { NumberCell } from "../NumberCell";

describe("NumberCell", () => {
	it("renders value with default precision 3", () => {
		render(<NumberCell value={3.412} />);
		expect(screen.getByText(/3\.412/)).toBeInTheDocument();
	});

	it("renders positive delta with ▲ and text-up class", () => {
		const { container } = render(<NumberCell value={3.412} delta={0.084} />);
		expect(screen.getByText(/▲/)).toBeInTheDocument();
		expect(container.querySelector(".text-up")).toBeInTheDocument();
	});

	it("renders negative delta with ▼ and text-down class", () => {
		const { container } = render(<NumberCell value={3.412} delta={-0.084} />);
		expect(screen.getByText(/▼/)).toBeInTheDocument();
		expect(container.querySelector(".text-down")).toBeInTheDocument();
	});

	it("renders zero delta with — and text-flat class", () => {
		const { container } = render(<NumberCell value={3.412} delta={0} />);
		expect(screen.getByText("—")).toBeInTheDocument();
		expect(container.querySelector(".text-flat")).toBeInTheDocument();
	});

	it("respects custom precision", () => {
		render(<NumberCell value={3.412} precision={1} />);
		expect(screen.getByText(/3\.4/)).toBeInTheDocument();
	});

	it("renders unit label", () => {
		render(<NumberCell value={3.412} unit="$/MMBtu" />);
		expect(screen.getByText("$/MMBtu")).toBeInTheDocument();
	});
});
