import { render, screen } from "@testing-library/react";
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
  },
  {
    user_id: "61cb184c-bbbb",
    n: 14,
    brier: 0.42,
    hit_rate: 0.43,
    mean_conviction: 85,
    calibration_gap: 42,
    qualifies: true,
  },
  {
    user_id: "thin-cccc",
    n: 3,
    brier: 0.1,
    hit_rate: 0.67,
    mean_conviction: 70,
    calibration_gap: 3,
    qualifies: false,
  },
];

describe("DeskCalibrationCard", () => {
  beforeEach(() => useDeskCalibrationMock.mockReset());

  it("renders analysts with calibration + flags overconfidence", () => {
    useDeskCalibrationMock.mockReturnValue({
      data: { analysts, min_resolved: 10 },
      isLoading: false,
    });
    render(<DeskCalibrationCard />);
    expect(screen.getByText("Analyst b7ccd4")).toBeInTheDocument();
    expect(screen.getByText("0.230")).toBeInTheDocument();
    expect(screen.getByText("+42 overconfident")).toBeInTheDocument();
  });

  it("withholds a score below the significance threshold", () => {
    useDeskCalibrationMock.mockReturnValue({
      data: { analysts, min_resolved: 10 },
      isLoading: false,
    });
    render(<DeskCalibrationCard />);
    // thin analyst (n=3) shows "need 7 more" instead of a Brier score
    expect(screen.getByText("need 7 more")).toBeInTheDocument();
  });

  it("shows empty state with no analysts", () => {
    useDeskCalibrationMock.mockReturnValue({
      data: { analysts: [], min_resolved: 10 },
      isLoading: false,
    });
    render(<DeskCalibrationCard />);
    expect(screen.getByText(/No resolved decisions yet/)).toBeInTheDocument();
  });
});
