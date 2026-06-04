import type { Bar } from "@/app/(app)/chart/types";
import type { IndicatorSeriesDTO } from "@/lib/api";
import { newSpec } from "@/lib/chart/indicatorRegistry";
import { render } from "@testing-library/react";
import { PriceChart } from "../PriceChart";

// v5: every series is created via addSeries(SeriesDefinition, options).
const addSeries = vi.fn((_def: unknown, _opts?: unknown) => ({
  setData: vi.fn(),
  update: vi.fn(),
}));

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addSeries,
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    takeScreenshot: vi.fn(),
    resize: vi.fn(),
    remove: vi.fn(),
  })),
  createSeriesMarkers: vi.fn(),
  CandlestickSeries: "CandlestickSeries",
  BarSeries: "BarSeries",
  AreaSeries: "AreaSeries",
  BaselineSeries: "BaselineSeries",
  LineSeries: "LineSeries",
  HistogramSeries: "HistogramSeries",
  ColorType: { Solid: "solid" },
  CrosshairMode: { Magnet: 1 },
  PriceScaleMode: { Normal: 0, Logarithmic: 1 },
}));

function lineSeriesCalls() {
  return addSeries.mock.calls.filter((c) => c[0] === "LineSeries");
}

const bars: Bar[] = [
  { ts: "2026-05-01T00:00:00Z", o: 3.4, h: 3.5, l: 3.3, c: 3.45, v: 10000 },
  { ts: "2026-05-02T00:00:00Z", o: 3.45, h: 3.55, l: 3.4, c: 3.5, v: 12000 },
];

const base = {
  eventMarkers: [],
  indicators: [],
  indicatorSeries: [],
  chartType: "candlestick" as const,
  logScale: false,
  showCurve: false,
  curve: [],
  patterns: [],
  autoTa: null,
  livePrice: null,
};

describe("PriceChart", () => {
  beforeEach(() => {
    addSeries.mockClear();
  });

  it("renders without crashing with valid bar data", () => {
    const { container } = render(<PriceChart {...base} bars={bars} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders without crashing with empty bars", () => {
    const { container } = render(<PriceChart {...base} bars={[]} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("adds one line series per paired visible indicator", () => {
    const ema = newSpec("ema", { period: 21 });
    const sma = newSpec("sma", { period: 50 });
    const indicatorSeries: IndicatorSeriesDTO[] = [
      {
        type: "ema",
        params: { period: 21, source: "close" },
        pane: "price",
        lines: [
          {
            role: "line",
            points: [
              { t: "2026-05-01T00:00:00Z", v: 3.4 },
              { t: "2026-05-02T00:00:00Z", v: 3.42 },
            ],
          },
        ],
      },
      {
        type: "sma",
        params: { period: 50, source: "close" },
        pane: "price",
        lines: [
          {
            role: "line",
            points: [
              { t: "2026-05-01T00:00:00Z", v: 3.41 },
              { t: "2026-05-02T00:00:00Z", v: 3.43 },
            ],
          },
        ],
      },
    ];
    render(
      <PriceChart
        {...base}
        bars={bars}
        indicators={[ema, sma]}
        indicatorSeries={indicatorSeries}
      />,
    );
    const lines = lineSeriesCalls();
    expect(lines).toHaveLength(2);
    // First spec (EMA) → its color/weight passed as the options arg.
    expect(lines[0][1]).toEqual(
      expect.objectContaining({ color: ema.color, lineWidth: ema.weight }),
    );
  });

  it("skips hidden indicators", () => {
    const ema = newSpec("ema", { period: 21 });
    const hidden = { ...newSpec("sma", { period: 50 }), visible: false };
    const indicatorSeries: IndicatorSeriesDTO[] = [
      {
        type: "ema",
        params: { period: 21, source: "close" },
        pane: "price",
        lines: [
          { role: "line", points: [{ t: "2026-05-01T00:00:00Z", v: 3.4 }] },
        ],
      },
      {
        type: "sma",
        params: { period: 50, source: "close" },
        pane: "price",
        lines: [
          { role: "line", points: [{ t: "2026-05-01T00:00:00Z", v: 3.41 }] },
        ],
      },
    ];
    render(
      <PriceChart
        {...base}
        bars={bars}
        indicators={[ema, hidden]}
        indicatorSeries={indicatorSeries}
      />,
    );
    expect(lineSeriesCalls()).toHaveLength(1);
  });

  it("does not crash if the API hasn't returned a series for a spec yet", () => {
    const ema = newSpec("ema", { period: 21 });
    const { container } = render(
      <PriceChart {...base} bars={bars} indicators={[ema]} />,
    );
    expect(container.firstChild).toBeInTheDocument();
    expect(lineSeriesCalls()).toHaveLength(0);
  });
});
