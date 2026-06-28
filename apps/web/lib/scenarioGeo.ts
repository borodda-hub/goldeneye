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

/** Natural-gas geography → glowing points + animated arcs. Every element is
 *  driven by a real shock + its sign-derived lean. */
function buildGasLayers(
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

// ── Crude oil (Brent) geography ──────────────────────────────────────────────
export const BRENT = { name: "Brent (North Sea)", lat: 58.0, lng: 1.5 };
export const HORMUZ = { name: "Strait of Hormuz", lat: 26.6, lng: 56.5 };
export const OPEC_PRODUCERS = [
  { name: "Ras Tanura (Saudi)", lat: 26.64, lng: 50.16 },
  { name: "Basra (Iraq)", lat: 30.5, lng: 47.8 },
  { name: "Fujairah (UAE)", lat: 25.12, lng: 56.34 },
];
export const CRUDE_REFINING = [
  { name: "Rotterdam (ARA)", lat: 51.9, lng: 4.5 },
  { name: "Singapore", lat: 1.29, lng: 103.85 },
  { name: "US Gulf Coast", lat: 29.7, lng: -93.5 },
];
export const CRUDE_STOCK_HUB = { name: "US Gulf / SPR", lat: 29.6, lng: -93.2 };
const CRUDE_GEO_REGIONS: Record<
  string,
  { name: string; lat: number; lng: number }
> = {
  hormuz: HORMUZ,
  russia: { name: "Russia (Primorsk/Urals)", lat: 60.0, lng: 28.7 },
  mideast: { name: "Middle East Gulf", lat: 27.0, lng: 51.0 },
  libya: { name: "Libya (Es Sider)", lat: 30.9, lng: 18.3 },
  venezuela: { name: "Venezuela (Jose)", lat: 10.1, lng: -64.7 },
};
const CRUDE_DEMAND: Record<string, { name: string; lat: number; lng: number }> =
  {
    china: { name: "China demand (Shandong)", lat: 31.2, lng: 121.5 },
    oecd: { name: "OECD Europe (ARA)", lat: 51.9, lng: 4.5 },
    us: { name: "US demand (USGC)", lat: 29.7, lng: -93.5 },
    global: { name: "Global seaborne", lat: 22.0, lng: 60.0 },
  };

/** Crude-oil geography → glowing points + animated arcs, all routed to the
 *  Brent benchmark node. Sign-derived lean, same as gas. */
function buildCrudeLayers(
  shocks: Shock[],
  palette: LeanPalette = DEFAULT_LEAN_COLOR,
): { points: GlobePoint[]; arcs: GlobeArc[] } {
  const points: GlobePoint[] = [
    {
      ...BRENT,
      label: "Brent (crude benchmark)",
      color: palette.neutral,
      size: 0.9,
      kind: "hub",
    },
  ];
  const arcs: GlobeArc[] = [];
  const seen = new Set<string>([BRENT.name]);

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
      color: palette[lean],
      size,
      kind: "locus",
    });
  };
  const toBrent = (
    p: { lat: number; lng: number; name: string },
    lean: Lean,
  ) => {
    arcs.push({
      startLat: p.lat,
      startLng: p.lng,
      endLat: BRENT.lat,
      endLng: BRENT.lng,
      color: [palette[lean], palette.neutral],
      label: `${p.name} → Brent`,
      kind: "flow",
    });
  };

  for (const s of shocks) {
    const lean = shockLean(s);
    if (s.type === "opec_supply") {
      for (const pr of OPEC_PRODUCERS) {
        addPoint(pr, lean, 0.6);
        toBrent(pr, lean);
      }
    } else if (s.type === "geopolitical_supply") {
      const r =
        CRUDE_GEO_REGIONS[s.region.toLowerCase()] ?? CRUDE_GEO_REGIONS.mideast;
      addPoint(r, lean, 0.75);
      toBrent(r, lean);
    } else if (s.type === "demand") {
      const d = CRUDE_DEMAND[s.region.toLowerCase()] ?? CRUDE_DEMAND.global;
      addPoint(d, lean, 0.75);
      toBrent(d, lean);
    } else if (s.type === "inventory") {
      addPoint(CRUDE_STOCK_HUB, lean, 0.6);
      toBrent(CRUDE_STOCK_HUB, lean);
    }
  }

  return { points, arcs };
}

// B5: only these instruments have a geographic scenario taxonomy. Everything else
// (ES/ZN and every non-energy asset class) renders an empty globe — never the
// Henry-Hub gas / Brent crude geography it has no business showing.
const GEO_TAXONOMY = new Set(["NG", "BZ"]);

/** True when the instrument has a defined scenario geography (NG or BZ). */
export function hasScenarioGeography(instrument: string): boolean {
  return GEO_TAXONOMY.has(instrument);
}

/** Dispatch to the right geography for the instrument (BZ = crude, NG = gas);
 *  empty for any instrument without a scenario taxonomy. */
export function buildGlobeLayers(
  shocks: Shock[],
  palette: LeanPalette = DEFAULT_LEAN_COLOR,
  instrument = "NG",
): { points: GlobePoint[]; arcs: GlobeArc[] } {
  if (!GEO_TAXONOMY.has(instrument)) return { points: [], arcs: [] };
  return instrument === "BZ"
    ? buildCrudeLayers(shocks, palette)
    : buildGasLayers(shocks, palette);
}

/** The pricing-benchmark label for the instrument (legend + framing). Empty for
 *  instruments without a scenario taxonomy. */
export function benchmarkOf(instrument: string): string {
  if (instrument === "BZ") return "Brent";
  if (instrument === "NG") return "Henry Hub";
  return "";
}

/** Faint reference infrastructure (real, static) for the instrument's market;
 *  empty for instruments without a scenario taxonomy. */
export function infraGeography(
  instrument: string,
): { name: string; lat: number; lng: number; role: string }[] {
  if (instrument === "BZ") {
    return [
      ...OPEC_PRODUCERS.map((p) => ({ ...p, role: "producer" })),
      { ...HORMUZ, role: "chokepoint" },
      ...CRUDE_REFINING.map((r) => ({ ...r, role: "refining hub" })),
      { ...CRUDE_STOCK_HUB, role: "storage" },
    ];
  }
  if (instrument !== "NG") return [];
  return [
    ...GULF_TERMINALS.map((t) => ({ ...t, role: "LNG terminal" })),
    ...EUROPE.map((e) => ({ ...e, role: "import hub" })),
    { ...STORAGE_HUB, role: "storage" },
  ];
}

/** Faint static trade corridors (the physical network behind shocks). */
export function networkCorridors(instrument: string): {
  from: { lat: number; lng: number };
  to: { lat: number; lng: number };
  label: string;
}[] {
  if (instrument === "BZ") {
    const arcs: {
      from: { lat: number; lng: number };
      to: { lat: number; lng: number };
      label: string;
    }[] = [];
    for (const p of OPEC_PRODUCERS) {
      arcs.push({ from: p, to: HORMUZ, label: `${p.name} → Strait of Hormuz` });
    }
    for (const r of CRUDE_REFINING) {
      arcs.push({ from: HORMUZ, to: r, label: `Strait of Hormuz → ${r.name}` });
    }
    return arcs;
  }
  if (instrument !== "NG") return [];
  const arcs: {
    from: { lat: number; lng: number };
    to: { lat: number; lng: number };
    label: string;
  }[] = [];
  for (const t of GULF_TERMINALS) {
    for (const e of EUROPE) {
      arcs.push({
        from: t,
        to: e,
        label: `${t.name} → ${e.name} · LNG corridor`,
      });
    }
  }
  return arcs;
}
