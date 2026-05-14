import type { Bar } from "@/app/(app)/chart/types";
import type { IndicatorSeriesDTO } from "@/lib/api";
import { newSpec } from "@/lib/chart/indicatorRegistry";
import { render } from "@testing-library/react";
import { PriceChart } from "../PriceChart";

const addLineSeries = vi.fn(() => ({ setData: vi.fn() }));

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      setData: vi.fn(),
      setMarkers: vi.fn(),
    })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn() })),
    addLineSeries,
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

describe("PriceChart", () => {
  beforeEach(() => {
    addLineSeries.mockClear();
  });

  it("renders without crashing with valid bar data", () => {
    const { container } = render(
      <PriceChart
        bars={bars}
        eventMarkers={[]}
        indicators={[]}
        indicatorSeries={[]}
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders without crashing with empty bars", () => {
    const { container } = render(
      <PriceChart
        bars={[]}
        eventMarkers={[]}
        indicators={[]}
        indicatorSeries={[]}
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("adds one line series per paired visible indicator", () => {
    const ema = newSpec("ema", { period: 21 });
    const sma = newSpec("sma", { period: 50 });
    const series: IndicatorSeriesDTO[] = [
      {
        type: "ema",
        params: { period: 21, source: "close" },
        points: [
          { t: "2026-05-01T00:00:00Z", v: 3.4 },
          { t: "2026-05-02T00:00:00Z", v: 3.42 },
        ],
      },
      {
        type: "sma",
        params: { period: 50, source: "close" },
        points: [
          { t: "2026-05-01T00:00:00Z", v: 3.41 },
          { t: "2026-05-02T00:00:00Z", v: 3.43 },
        ],
      },
    ];
    render(
      <PriceChart
        bars={bars}
        eventMarkers={[]}
        indicators={[ema, sma]}
        indicatorSeries={series}
      />,
    );
    expect(addLineSeries).toHaveBeenCalledTimes(2);
    // First spec is EMA → its color was passed to addLineSeries
    expect(addLineSeries).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ color: ema.color, lineWidth: ema.weight }),
    );
  });

  it("skips hidden indicators", () => {
    const ema = newSpec("ema", { period: 21 });
    const hidden = { ...newSpec("sma", { period: 50 }), visible: false };
    const series: IndicatorSeriesDTO[] = [
      {
        type: "ema",
        params: { period: 21, source: "close" },
        points: [{ t: "2026-05-01T00:00:00Z", v: 3.4 }],
      },
      {
        type: "sma",
        params: { period: 50, source: "close" },
        points: [{ t: "2026-05-01T00:00:00Z", v: 3.41 }],
      },
    ];
    render(
      <PriceChart
        bars={bars}
        eventMarkers={[]}
        indicators={[ema, hidden]}
        indicatorSeries={series}
      />,
    );
    expect(addLineSeries).toHaveBeenCalledTimes(1);
  });

  it("does not crash if the API hasn't returned a series for a spec yet", () => {
    const ema = newSpec("ema", { period: 21 });
    const { container } = render(
      <PriceChart
        bars={bars}
        eventMarkers={[]}
        indicators={[ema]}
        indicatorSeries={[]}
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
    expect(addLineSeries).not.toHaveBeenCalled();
  });
});
