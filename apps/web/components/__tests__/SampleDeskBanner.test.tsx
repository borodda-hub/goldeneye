import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const useCalibrationMock = vi.fn();
vi.mock("@/lib/queries", () => ({
  useCalibration: (...args: unknown[]) => useCalibrationMock(...args),
}));
vi.mock("@/lib/clerk", () => ({ clerkEnabled: false }));

import { SampleDeskBanner } from "../SampleDeskBanner";

function bucket(over: Record<string, unknown>) {
  return {
    label: "80-100",
    lower_pct: 80,
    upper_pct: 100,
    claimed_mean: 87.3,
    total_count: 60,
    resolved_count: 52,
    hit_count: 15,
    hit_rate: 15 / 52,
    ...over,
  };
}

describe("SampleDeskBanner (issue #8 — live-derived figure)", () => {
  it("quotes the live top-conviction bucket when n ≥ 10 and the miss is material", () => {
    useCalibrationMock.mockReturnValue({
      data: {
        buckets: [
          bucket({ label: "0-20", claimed_mean: 12, hit_rate: 0.5 }),
          bucket({}),
        ],
      },
    });
    const { container } = render(<SampleDeskBanner />);
    // 87.3 → ~87 claimed; 15/52 → ~29 realized — derived, not hardcoded.
    expect(container.textContent).toContain("~87% claimed");
    expect(container.textContent).toContain("~29% realized");
  });

  it("stays qualitative (no numbers) when no bucket has a scoreable sample", () => {
    useCalibrationMock.mockReturnValue({
      data: { buckets: [bucket({ resolved_count: 3 })] },
    });
    const { container } = render(<SampleDeskBanner />);
    expect(container.textContent).not.toContain("% claimed");
    expect(container.textContent).toContain("claimed conviction compares");
  });

  it("stays qualitative while calibration is still loading", () => {
    useCalibrationMock.mockReturnValue({ data: undefined });
    const { container } = render(<SampleDeskBanner />);
    expect(container.textContent).not.toContain("% claimed");
    // The honesty label itself never depends on the fetch.
    expect(container.textContent).toContain("not a real analyst track record");
  });
});
