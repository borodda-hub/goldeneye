import type { FuturesCurvePoint } from "@/app/(app)/dashboard/types";
import { render, screen } from "@testing-library/react";
import { FuturesCurveCard } from "../FuturesCurveCard";

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const curve: FuturesCurvePoint[] = [
  { contract_code: "NGF26", expiry: "2026-01-27", mid: 3.456 },
  { contract_code: "NGG26", expiry: "2026-02-24", mid: 3.512 },
];

describe("FuturesCurveCard", () => {
  it("renders Futures Curve label", () => {
    render(<FuturesCurveCard curve={curve} />);
    expect(screen.getByText(/futures curve/i)).toBeInTheDocument();
  });

  it("renders chart container when data provided", () => {
    render(<FuturesCurveCard curve={curve} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders empty state when curve is empty", () => {
    render(<FuturesCurveCard curve={[]} />);
    expect(screen.getByText("No curve data.")).toBeInTheDocument();
  });
});
