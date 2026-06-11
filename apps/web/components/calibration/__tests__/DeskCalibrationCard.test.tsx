import { render, screen, within } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

const useDeskCalibrationMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useDeskCalibration: () => useDeskCalibrationMock(),
}));

import { DeskCalibrationCard } from "../DeskCalibrationCard";

const analysts = [
  {
    user_id: "b7ccd47d-aaaa",
    n: 14,
    brier: 0.23,
    hit_rate: 0.64,
    mean_conviction: 65,
    calibration_gap: 0.7,
    qualifies: true,
    wilson_low: 0.55,
    wilson_high: 0.88,
    verdict: "skill" as const,
  },
  {
    user_id: "61cb184c-bbbb",
    n: 14,
    brier: 0.42,
    hit_rate: 0.43,
    mean_conviction: 85,
    calibration_gap: 42,
    qualifies: true,
    wilson_low: 0.21,
    wilson_high: 0.67,
    verdict: "luck" as const,
  },
  {
    user_id: "thin-cccc",
    n: 3,
    brier: 0.1,
    hit_rate: 0.67,
    mean_conviction: 70,
    calibration_gap: 3,
    qualifies: false,
    wilson_low: null,
    wilson_high: null,
    verdict: "insufficient" as const,
  },
];

const data = { analysts, min_resolved: 10, baseline: 0.5 };

describe("DeskCalibrationCard", () => {
  beforeEach(() => useDeskCalibrationMock.mockReset());

  it("renders analysts with calibration + flags overconfidence", () => {
    useDeskCalibrationMock.mockReturnValue({ data, isLoading: false });
    render(<DeskCalibrationCard />);
    expect(screen.getByText("Analyst b7ccd4")).toBeInTheDocument();
    expect(screen.getByText("0.230")).toBeInTheDocument();
    expect(screen.getByText("+42 overconfident")).toBeInTheDocument();
  });

  it("renders the skill / luck / insufficient verdict badges", () => {
    useDeskCalibrationMock.mockReturnValue({ data, isLoading: false });
    render(<DeskCalibrationCard />);
    // Scope to the table — the footnote legend reuses the same words.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Skill")).toBeInTheDocument();
    expect(table.getByText("Luck")).toBeInTheDocument();
    expect(table.getByText("Insufficient")).toBeInTheDocument();
  });

  it("shows the Wilson CI on the hit cell for qualifying rows", () => {
    useDeskCalibrationMock.mockReturnValue({ data, isLoading: false });
    render(<DeskCalibrationCard />);
    // skill row: hit 64% with CI [55–88%]
    expect(screen.getByText("[55–88%]")).toBeInTheDocument();
  });

  it("frames the test as refusing to call noise skill (S6 copy)", () => {
    useDeskCalibrationMock.mockReturnValue({ data, isLoading: false });
    render(<DeskCalibrationCard />);
    expect(
      screen.getByText(/correctly refuses to call noise skill/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/random desk lands on\s+Luck by design/),
    ).toBeInTheDocument();
  });

  it("withholds a score below the significance threshold", () => {
    useDeskCalibrationMock.mockReturnValue({ data, isLoading: false });
    render(<DeskCalibrationCard />);
    // thin analyst (n=3) shows "need 7 more" instead of a Brier score
    expect(screen.getByText("need 7 more")).toBeInTheDocument();
  });

  it("shows empty state with no analysts", () => {
    useDeskCalibrationMock.mockReturnValue({
      data: { analysts: [], min_resolved: 10, baseline: 0.5 },
      isLoading: false,
    });
    render(<DeskCalibrationCard />);
    expect(screen.getByText(/No resolved decisions yet/)).toBeInTheDocument();
  });
});
