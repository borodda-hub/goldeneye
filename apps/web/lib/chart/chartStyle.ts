"use client";

/**
 * User-customizable chart appearance — the cosmetic settings exposed by the
 * Chart Settings panel. Persisted globally (across symbols) to localStorage.
 * Values map directly onto Lightweight Charts `applyOptions()` so the chart
 * restyles live without a rebuild. `crosshairStyle` is an LWC LineStyle
 * (0 Solid · 1 Dotted · 2 Dashed · 3 LargeDashed · 4 SparseDotted).
 */
export type ChartThemeName = "dark" | "light" | "gold" | "custom";

export interface ChartStyle {
  theme: ChartThemeName;
  // candles / bars
  upColor: string;
  downColor: string;
  wickUpColor: string;
  wickDownColor: string;
  borderVisible: boolean;
  hollowUp: boolean;
  // canvas
  background: string;
  gradient: boolean;
  backgroundBottom: string;
  gridColor: string;
  gridVisible: boolean;
  textColor: string;
  fontSize: number;
  // crosshair
  crosshairColor: string;
  crosshairStyle: number;
  crosshairMagnet: boolean;
}

const DARK: ChartStyle = {
  theme: "dark",
  upColor: "#6dd58c",
  downColor: "#e87575",
  wickUpColor: "#6dd58c",
  wickDownColor: "#e87575",
  borderVisible: false,
  hollowUp: false,
  background: "#0a0a09",
  gradient: false,
  backgroundBottom: "#000000",
  gridColor: "#2a2a26",
  gridVisible: true,
  textColor: "#b4afa4",
  fontSize: 11,
  crosshairColor: "#979281",
  crosshairStyle: 2,
  crosshairMagnet: true,
};

const LIGHT: ChartStyle = {
  ...DARK,
  theme: "light",
  upColor: "#26a69a",
  downColor: "#ef5350",
  wickUpColor: "#26a69a",
  wickDownColor: "#ef5350",
  background: "#ffffff",
  gradient: false,
  backgroundBottom: "#f3f4f6",
  gridColor: "#e1e3e6",
  textColor: "#131722",
  crosshairColor: "#9598a1",
};

// Warm "gold terminal" theme — brand-tinted dark canvas, but candles keep the
// functional green/red so up vs down stays unmistakable.
const GOLD: ChartStyle = {
  ...DARK,
  theme: "gold",
  background: "#100b04",
  gradient: true,
  backgroundBottom: "#070502",
  gridColor: "#2a2014",
  textColor: "#e8c074",
  crosshairColor: "#c9a35c",
  borderVisible: true,
  wickUpColor: "#6dd58c",
  wickDownColor: "#e87575",
};

export const CHART_THEMES: Record<"dark" | "light" | "gold", ChartStyle> = {
  dark: DARK,
  light: LIGHT,
  gold: GOLD,
};

export const DEFAULT_CHART_STYLE: ChartStyle = DARK;

const STORAGE_KEY = "goldeneye:chart:style";

export function loadChartStyle(): ChartStyle {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      // Merge over defaults so a new field added later doesn't break old saves.
      return { ...DARK, ...(JSON.parse(raw) as Partial<ChartStyle>) };
    }
  } catch {
    // localStorage unavailable — fall through to default.
  }
  return DARK;
}

export function saveChartStyle(style: ChartStyle): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(style));
  } catch {
    // ignore — incognito / quota.
  }
}
