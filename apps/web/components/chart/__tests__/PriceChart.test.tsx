import { render, screen } from "@testing-library/react";
import { PriceChart } from "../PriceChart";
import type { Bar, OverlayPoint } from "@/app/(app)/chart/types";

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      setData: vi.fn(),
      setMarkers: vi.fn(),
    })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn() })),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn(), borderColor: "" })),
    resize: vi.fn(),
    remove: vi.fn(),
  })),
  ColorType: { Solid: "solid" },
  CrosshairMode: { Magnet: 1 },
}));

const bars: Bar[] = [
  { ts: "2026-05-01T00:00:00Z", o: 3.4, h: 3.5, l: 3.3, c: 3.45, v: 10000 },
  { ts: "2026-05-02T00:00:00Z", o: 3.45, h: 3.55, l: 3.4, c: 3.5, v: 12000 },
];

const overlays: { sma_20: OverlayPoint[]; ema_50: OverlayPoint[] } = {
  sma_20: [
    { ts: "2026-05-01T00:00:00Z", v: 3.42 },
    { ts: "2026-05-02T00:00:00Z", v: 3.44 },
  ],
  ema_50: [],
};

describe("PriceChart", () => {
  it("renders without crashing with valid bar data", () => {
    const { container } = render(
      <PriceChart
        bars={bars}
        overlays={overlays}
        eventMarkers={[]}
        showSMA20={true}
        showEMA50={false}
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders without crashing with empty bars", () => {
    const { container } = render(
      <PriceChart
        bars={[]}
        overlays={{ sma_20: [], ema_50: [] }}
        eventMarkers={[]}
        showSMA20={false}
        showEMA50={false}
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });
});
