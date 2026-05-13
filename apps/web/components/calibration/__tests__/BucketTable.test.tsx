import { render, screen } from "@testing-library/react";
import type { CalibrationBucket } from "@/lib/api";
import { BucketTable } from "../BucketTable";

const buckets: CalibrationBucket[] = [
  {
    label: "0-20",
    lower_pct: 0,
    upper_pct: 20,
    claimed_mean: null,
    total_count: 0,
    resolved_count: 0,
    hit_count: 0,
    hit_rate: null,
  },
  {
    label: "60-80",
    lower_pct: 60,
    upper_pct: 80,
    claimed_mean: 70.0,
    total_count: 14,
    resolved_count: 12,
    hit_count: 9,
    hit_rate: 9 / 12,
  },
  {
    label: "80-100",
    lower_pct: 80,
    upper_pct: 100,
    claimed_mean: 85.0,
    total_count: 2,
    resolved_count: 2,
    hit_count: 1,
    hit_rate: null, // below threshold
  },
];

describe("BucketTable", () => {
  it("renders one row per bucket", () => {
    render(<BucketTable buckets={buckets} />);
    expect(screen.getByText("0-20%")).toBeInTheDocument();
    expect(screen.getByText("60-80%")).toBeInTheDocument();
    expect(screen.getByText("80-100%")).toBeInTheDocument();
  });

  it("renders the hit rate as a percentage for the 60-80 band", () => {
    render(<BucketTable buckets={buckets} />);
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("renders the 'need 3+' caveat for buckets under threshold", () => {
    render(<BucketTable buckets={buckets} />);
    expect(screen.getByText(/n=2 \(need 3\+\)/)).toBeInTheDocument();
  });

  it("renders an em-dash for null claimed_mean", () => {
    render(<BucketTable buckets={buckets} />);
    // First bucket has total_count=0 → claimed_mean is null → shown as "—"
    const cells = screen.getAllByText("—");
    expect(cells.length).toBeGreaterThan(0);
  });
});
