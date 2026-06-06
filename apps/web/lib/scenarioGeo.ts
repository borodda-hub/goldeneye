import type { Shock } from "@/app/(app)/scenarios/types";
import { type Lean, shockLean } from "./scenarioLean";

/** Static geography for the scenario impact globe. Approximate coordinates —
 *  enough to make the shock's mechanism legible (the picture is the thesis). */
export const HENRY_HUB = { name: "Henry Hub", lat: 29.97, lng: -92.0 };

export const GULF_TERMINALS = [
  { name: "Sabine Pass", lat: 29.73, lng: -93.87 },
  { name: "Freeport", lat: 28.95, lng: -95.31 },
  { name: "Corpus Christi", lat: 27.84, lng: -97.06 },
  { name: "Cameron", lat: 29.78, lng: -93.33 },
];
export const EUROPE = [
  { name: "UK (NBP)", lat: 51.5, lng: -0.1 },
  { name: "Netherlands (TTF)", lat: 51.9, lng: 4.5 },
];
const BASIN = { name: "Appalachia (Marcellus)", lat: 40.0, lng: -78.0 };
export const STORAGE_HUB = { name: "Interior storage", lat: 38.5, lng: -94.0 };
const REGIONS: Record<string, { name: string; lat: number; lng: number }> = {
  northeast: { name: "Northeast demand", lat: 42.0, lng: -73.5 },
  midwest: { name: "Midwest demand", lat: 41.9, lng: -93.6 },
  south: { name: "South demand", lat: 32.8, lng: -96.8 },
  west: { name: "West demand", lat: 39.5, lng: -119.8 },
};

/** Lean → color. Defaults are the brand palette; the globe passes the active
 *  theme's tokens so the picture tracks palette changes. */
export type LeanPalette = Record<Lean, string>;
const DEFAULT_LEAN_COLOR: LeanPalette = {
  bullish: "#41d18b", // up
  bearish: "#f0616d", // down
  neutral: "#c9a35c", // gold accent
};

export interface GlobePoint {
  lat: number;
  lng: number;
  label: string;
  color: string;
  size: number;
  kind: "hub" | "locus" | "infra";
}
export interface GlobeArc {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  color: [string, string];
  label: string;
  kind: "flow" | "network";
}

/** Translate the current shocks into glowing points + animated arcs. Every
 *  element is driven by a real shock + its sign-derived lean. */
export function buildGlobeLayers(
  shocks: Shock[],
  palette: LeanPalette = DEFAULT_LEAN_COLOR,
): {
  points: GlobePoint[];
  arcs: GlobeArc[];
} {
  const LEAN_COLOR = palette;
  const points: GlobePoint[] = [
    {
      ...HENRY_HUB,
      label: "Henry Hub (NG benchmark)",
      color: palette.neutral,
      size: 0.9,
      kind: "hub",
    },
  ];
  const arcs: GlobeArc[] = [];
  const seen = new Set<string>([HENRY_HUB.name]);

  const addPoint = (
    p: { name: string; lat: number; lng: number },
    lean: Lean,
    size = 0.6,
  ) => {
    if (seen.has(p.name)) return;
    seen.add(p.name);
    points.push({
      lat: p.lat,
      lng: p.lng,
      label: p.name,
      color: LEAN_COLOR[lean],
      size,
      kind: "locus",
    });
  };
  const toHub = (p: { lat: number; lng: number; name: string }, lean: Lean) => {
    arcs.push({
      startLat: p.lat,
      startLng: p.lng,
      endLat: HENRY_HUB.lat,
      endLng: HENRY_HUB.lng,
      color: [LEAN_COLOR[lean], palette.neutral],
      label: `${p.name} → Henry Hub`,
      kind: "flow",
    });
  };

  for (const s of shocks) {
    const lean = shockLean(s);
    if (s.type === "weather") {
      const r = REGIONS[s.region.toLowerCase()] ?? REGIONS.northeast;
      addPoint(r, lean, 0.7);
      toHub(r, lean);
    } else if (s.type === "lng_export") {
      // Trans-Atlantic flow arcs — the global story.
      for (const t of GULF_TERMINALS.slice(0, 3)) {
        addPoint(t, lean, 0.55);
        for (const e of EUROPE) {
          addPoint(e, lean, 0.5);
          arcs.push({
            startLat: t.lat,
            startLng: t.lng,
            endLat: e.lat,
            endLng: e.lng,
            color: [LEAN_COLOR[lean], LEAN_COLOR[lean]],
            label: `${t.name} → ${e.name}`,
            kind: "flow",
          });
        }
      }
    } else if (s.type === "production") {
      addPoint(BASIN, lean, 0.7);
      toHub(BASIN, lean);
    } else if (s.type === "storage") {
      addPoint(STORAGE_HUB, lean, 0.6);
      toHub(STORAGE_HUB, lean);
    }
  }

  return { points, arcs };
}
