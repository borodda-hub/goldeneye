/**
 * Chart-indicator registry (Phase 15).
 *
 * The frontend representation of an indicator spec. Mirrors the backend
 * `IndicatorSpec` shape but adds presentation properties (color, weight)
 * so the chart layer can render without re-resolving design tokens.
 *
 * Phase 15 ships only the moving-average family. The registry is structured
 * so Phase 16 (channels) and Phase 17 (trend strength) bolt on more types
 * without rewriting consumers — add a member to `MA_TYPES`/`IndicatorType`
 * and a defaults row, and the picker / chart wiring picks it up.
 */
import { colors } from "@/lib/colors";

export const MA_TYPES = [
  "sma",
  "ema",
  "wma",
  "hma",
  "dema",
  "tema",
  "vwma",
] as const;
export type MAType = (typeof MA_TYPES)[number];

/** Phase 23 — oscillators (sub-pane) + volatility bands (price overlay). */
export const OSC_TYPES = [
  "rsi",
  "macd",
  "stoch",
  "adx",
  "atr",
  "bb",
  "kc",
  "dc",
] as const;
export type OscType = (typeof OSC_TYPES)[number];

export type IndicatorType = MAType | OscType;

export const PRICE_SOURCES = [
  "close",
  "open",
  "high",
  "low",
  "hl2",
  "hlc3",
] as const;
export type PriceSource = (typeof PRICE_SOURCES)[number];

export type LineWeight = 1 | 2 | 3;

export interface IndicatorSpec {
  /** Stable id so React keys / localStorage rows survive edits. */
  id: string;
  type: IndicatorType;
  period: number;
  source: PriceSource;
  /** Multi-param indicators (MACD, Bollinger, …) store their params here.
   *  MAs use `period`/`source`; for oscillators/bands `period` is unused. */
  params?: Record<string, number>;
  /** Raw chart color (Lightweight Charts takes hex). Always a token from `colors`. */
  color: string;
  weight: LineWeight;
  /** When false, the series is hidden but kept in storage so toggle is cheap. */
  visible: boolean;
  /** Optional group tag — currently used by the Ribbon preset for bulk remove. */
  tag?: string;
}

interface Defaults {
  period: number;
  source: PriceSource;
  color: string;
  weight: LineWeight;
}

export const DEFAULTS: Record<MAType, Defaults> = {
  sma: { period: 20, source: "close", color: colors.accent, weight: 2 },
  ema: { period: 21, source: "close", color: colors.accentBright, weight: 2 },
  wma: { period: 20, source: "close", color: colors.accentDeep, weight: 2 },
  hma: { period: 21, source: "close", color: colors.amber, weight: 2 },
  dema: { period: 21, source: "close", color: colors.cyan, weight: 2 },
  tema: { period: 21, source: "close", color: colors.violet, weight: 2 },
  vwma: { period: 20, source: "close", color: colors.accent, weight: 2 },
};

export const MA_LABEL: Record<MAType, string> = {
  sma: "SMA",
  ema: "EMA",
  wma: "WMA",
  hma: "HMA (Hull)",
  dema: "DEMA",
  tema: "TEMA",
  vwma: "VWMA",
};

export const PERIOD_MIN = 2;
export const PERIOD_MAX = 500;

/** Catalog for oscillators / bands: presentation + default params + pane. */
export interface OscDef {
  label: string;
  category: "Momentum" | "Trend" | "Volatility";
  pane: "price" | "sub";
  paramOrder: string[];
  defaults: Record<string, number>;
  color: string;
}

export const OSC_CATALOG: Record<OscType, OscDef> = {
  rsi: {
    label: "RSI",
    category: "Momentum",
    pane: "sub",
    paramOrder: ["period"],
    defaults: { period: 14 },
    color: colors.cyan,
  },
  macd: {
    label: "MACD",
    category: "Momentum",
    pane: "sub",
    paramOrder: ["fast", "slow", "signal"],
    defaults: { fast: 12, slow: 26, signal: 9 },
    color: colors.accentBright,
  },
  stoch: {
    label: "Stochastic",
    category: "Momentum",
    pane: "sub",
    paramOrder: ["k", "d", "smooth"],
    defaults: { k: 14, d: 3, smooth: 3 },
    color: colors.violet,
  },
  adx: {
    label: "ADX",
    category: "Trend",
    pane: "sub",
    paramOrder: ["period"],
    defaults: { period: 14 },
    color: colors.amber,
  },
  atr: {
    label: "ATR",
    category: "Volatility",
    pane: "sub",
    paramOrder: ["period"],
    defaults: { period: 14 },
    color: colors.accent,
  },
  bb: {
    label: "Bollinger",
    category: "Volatility",
    pane: "price",
    paramOrder: ["period", "stddev"],
    defaults: { period: 20, stddev: 2 },
    color: colors.accentDeep,
  },
  kc: {
    label: "Keltner",
    category: "Volatility",
    pane: "price",
    paramOrder: ["period", "mult"],
    defaults: { period: 20, mult: 2 },
    color: colors.accentDeep,
  },
  dc: {
    label: "Donchian",
    category: "Volatility",
    pane: "price",
    paramOrder: ["period"],
    defaults: { period: 20 },
    color: colors.accentDeep,
  },
};

export function isMaType(t: IndicatorType): t is MAType {
  return (MA_TYPES as readonly string[]).includes(t);
}

export function specToLabel(s: IndicatorSpec): string {
  if (isMaType(s.type)) return `${s.type.toUpperCase()}(${s.period})`;
  const def = OSC_CATALOG[s.type];
  const vals = def.paramOrder.map((k) => s.params?.[k] ?? def.defaults[k]);
  return `${def.label}(${vals.join(",")})`;
}

/** Single spec → query fragment. MAs: `type:period[:source]`; oscillators/
 *  bands: `type:p1:p2:…` in the catalog's param order. */
export function specToQueryFragment(s: IndicatorSpec): string {
  if (isMaType(s.type)) {
    return s.source === "close"
      ? `${s.type}:${s.period}`
      : `${s.type}:${s.period}:${s.source}`;
  }
  const def = OSC_CATALOG[s.type];
  const vals = def.paramOrder.map((k) => s.params?.[k] ?? def.defaults[k]);
  return [s.type, ...vals].join(":");
}

/** Build a preset spec (default params) for an oscillator / band type. */
export function presetSpec(type: OscType): IndicatorSpec {
  const def = OSC_CATALOG[type];
  return {
    id: nextId(),
    type,
    period: def.defaults.period ?? 14,
    source: "close",
    params: { ...def.defaults },
    color: def.color,
    weight: 2,
    visible: true,
  };
}

/** Join visible specs into the comma-separated `spec=` value the API expects. */
export function specsToQueryParam(specs: IndicatorSpec[]): string {
  return specs
    .filter((s) => s.visible)
    .map(specToQueryFragment)
    .join(",");
}

let _idCounter = 0;
function nextId(): string {
  _idCounter += 1;
  return `ind_${Date.now().toString(36)}_${_idCounter.toString(36)}`;
}

/** Build a fresh spec with sensible defaults for the given type. */
export function newSpec(
  type: MAType,
  overrides: Partial<Omit<IndicatorSpec, "id" | "type">> = {},
): IndicatorSpec {
  const d = DEFAULTS[type];
  return {
    id: nextId(),
    type,
    period: overrides.period ?? d.period,
    source: overrides.source ?? d.source,
    color: overrides.color ?? d.color,
    weight: overrides.weight ?? d.weight,
    visible: overrides.visible ?? true,
    tag: overrides.tag,
  };
}

/** Ribbon preset: 12 EMAs at Fibonacci-ish periods with a gold→amber ramp.
 *  Tagged `"ribbon"` so the picker can offer a single-click bulk-remove. */
export const RIBBON_TAG = "ribbon";
export const RIBBON_PERIODS = [
  5, 8, 13, 21, 34, 55, 89, 100, 144, 200, 233, 377,
];
/** 12-step interpolation between colors.accentDeep (#8a6f3a) and colors.amber (#f0b429). */
export const RIBBON_PALETTE = [
  "#8a6f3a",
  "#937538",
  "#9c7c37",
  "#a58235",
  "#af8934",
  "#b88f32",
  "#c19531",
  "#ca9c2f",
  "#d4a22e",
  "#dda82c",
  "#e6af2b",
  "#f0b429",
];

/** Build the 12 ribbon specs. Stable enough that two consecutive calls
 *  produce different ids (so the React keys stay unique). */
export function ribbonSpecs(): IndicatorSpec[] {
  return RIBBON_PERIODS.map((period, i) =>
    newSpec("ema", {
      period,
      color: RIBBON_PALETTE[i],
      weight: 1,
      tag: RIBBON_TAG,
    }),
  );
}

export function hasRibbon(specs: IndicatorSpec[]): boolean {
  return specs.some((s) => s.tag === RIBBON_TAG);
}

export function withoutRibbon(specs: IndicatorSpec[]): IndicatorSpec[] {
  return specs.filter((s) => s.tag !== RIBBON_TAG);
}

/** Per-symbol localStorage key for the active indicator set. */
export function storageKey(symbol: string): string {
  return `ngti.chart.indicators.${symbol.toUpperCase()}`;
}

export function isValidPeriod(n: number): boolean {
  return Number.isInteger(n) && n >= PERIOD_MIN && n <= PERIOD_MAX;
}
