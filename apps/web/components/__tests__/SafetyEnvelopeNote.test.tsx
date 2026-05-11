import { render, screen, fireEvent } from "@testing-library/react";
import { SafetyEnvelopeNote } from "../SafetyEnvelopeNote";

const envelope = {
	confidence: "medium",
	caveats: ["Model outputs are statistical inferences only.", "Based on synthetic mock data."],
	as_of: "2026-05-10T12:00:00",
	disclaimer: "For research purposes only.",
};

describe("SafetyEnvelopeNote", () => {
	it("shows confidence level", () => {
		render(<SafetyEnvelopeNote envelope={envelope} />);
		expect(screen.getByText(/medium/i)).toBeInTheDocument();
	});

	it("shows as_of date", () => {
		render(<SafetyEnvelopeNote envelope={envelope} />);
		expect(screen.getByText(/2026-05-10/)).toBeInTheDocument();
	});

	it("shows first caveat after expanding", () => {
		render(<SafetyEnvelopeNote envelope={envelope} />);
		fireEvent.click(screen.getByRole("button"));
		expect(screen.getByText(/statistical inferences/i)).toBeInTheDocument();
	});
});
