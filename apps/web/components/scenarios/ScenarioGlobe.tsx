"use client";

import type { Shock } from "@/app/(app)/scenarios/types";
import {
  type GlobeArc,
  type GlobePoint,
  benchmarkOf,
  buildGlobeLayers,
  hasScenarioGeography,
  infraGeography,
  networkCorridors,
} from "@/lib/scenarioGeo";
import { rgba, useThemePalette } from "@/lib/useThemePalette";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";

// Bundled same-origin (the unpkg dataset URL 404s) so outlines always load.
const COUNTRIES_URL = "/geo/countries-110m.geojson";
// Standard satellite imagery (NASA blue-marble) + topology bump for relief.
const SAT_IMAGE =
  "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";
const SAT_BUMP = "https://unpkg.com/three-globe/example/img/earth-topology.png";
const HEIGHT = 440;
// Default camera framing per market — gas centers on the N. Atlantic, crude on
// the Europe→Gulf axis where Brent + the producing regions sit.
const POV_BY_INSTRUMENT: Record<
  string,
  { lat: number; lng: number; altitude: number }
> = {
  NG: { lat: 38, lng: -45, altitude: 2.0 },
  BZ: { lat: 34, lng: 28, altitude: 2.2 },
};
const defaultPov = (instrument: string) =>
  POV_BY_INSTRUMENT[instrument] ?? POV_BY_INSTRUMENT.NG;

type GlobeStyle = "vector" | "satellite";

/** Center + altitude that frames a set of loci (the active scenario geography). */
function frameView(
  pts: GlobePoint[],
  fallback: { lat: number; lng: number; altitude: number },
) {
  if (pts.length <= 1) return { ...fallback };
  const lats = pts.map((p) => p.lat);
  const lngs = pts.map((p) => p.lng);
  const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const lng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
  const span = Math.max(
    Math.max(...lats) - Math.min(...lats),
    Math.max(...lngs) - Math.min(...lngs),
  );
  const altitude = Math.min(2.8, Math.max(1.1, span / 45 + 0.9));
  return { lat, lng, altitude };
}

/**
 * The scenario impact globe. Renders a scenario's geography — glowing loci and
 * animated arcs colored by each shock's directional lean — in one of two looks:
 * "vector" (soft country outlines on a dark sphere, on-brand) or "satellite"
 * (standard NASA blue-marble imagery). View controls (rotate / reset / frame)
 * and toggleable reference layers (infrastructure, flow network, graticule) let
 * you read the mechanism. Client-only (parent imports it ssr:false).
 */
export function ScenarioGlobe({
  shocks,
  instrument = "NG",
}: {
  shocks: Shock[];
  instrument?: string;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [width, setWidth] = useState(640);
  const [style, setStyle] = useState<GlobeStyle>("vector");
  const [countries, setCountries] = useState<{ features: object[] }>({
    features: [],
  });

  // Controls + layer toggles.
  const [autoRotate, setAutoRotate] = useState(true);
  const [showInfra, setShowInfra] = useState(true);
  const [showNetwork, setShowNetwork] = useState(false);
  const [showGrid, setShowGrid] = useState(false);

  const theme = useThemePalette();
  const leanPalette = useMemo(
    () => ({
      bullish: rgba(theme.up, 1),
      bearish: rgba(theme.down, 1),
      neutral: rgba(theme.accent, 1),
    }),
    [theme],
  );
  const { points, arcs } = useMemo(
    () => buildGlobeLayers(shocks, leanPalette, instrument),
    [shocks, leanPalette, instrument],
  );

  // Faint reference infrastructure, minus any locus the active scenario already
  // lights up (so they don't double-plot).
  const infraPoints = useMemo<GlobePoint[]>(() => {
    if (!showInfra) return [];
    const active = new Set(points.map((p) => p.label));
    return infraGeography(instrument)
      .filter((i) => !active.has(i.name))
      .map((i) => ({
        lat: i.lat,
        lng: i.lng,
        label: `${i.name} · ${i.role}`,
        color: rgba(theme.accent, 0.5),
        size: 0.32,
        kind: "infra" as const,
      }));
  }, [showInfra, points, theme, instrument]);

  // Faint static trade corridors — the physical network behind shocks.
  const networkArcs = useMemo<GlobeArc[]>(() => {
    if (!showNetwork) return [];
    const c = rgba(theme.accent, 0.22);
    return networkCorridors(instrument).map((n) => ({
      startLat: n.from.lat,
      startLng: n.from.lng,
      endLat: n.to.lat,
      endLng: n.to.lng,
      color: [c, c] as [string, string],
      label: n.label,
      kind: "network" as const,
    }));
  }, [showNetwork, theme, instrument]);

  const allPoints = useMemo(
    () => [...infraPoints, ...points],
    [infraPoints, points],
  );
  const allArcs = useMemo(() => [...networkArcs, ...arcs], [networkArcs, arcs]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setWidth(e.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    fetch(COUNTRIES_URL)
      .then((r) => r.json())
      .then((d) => setCountries(d))
      .catch(() => {});
  }, []);

  // Dark sphere for the vector look (transparent in satellite mode so imagery shows).
  const vectorMaterial = useMemo(
    () => new THREE.MeshPhongMaterial({ color: "#0b0b0a", shininess: 6 }),
    [],
  );

  const applyAutoRotate = useCallback((on: boolean) => {
    try {
      const c = globeRef.current?.controls() as
        | { autoRotate: boolean; autoRotateSpeed: number }
        | undefined;
      if (c) {
        c.autoRotate = on;
        c.autoRotateSpeed = 0.5;
      }
    } catch {}
  }, []);

  const pov = useMemo(() => defaultPov(instrument), [instrument]);

  const onReady = useCallback(() => {
    applyAutoRotate(autoRotate);
    try {
      globeRef.current?.pointOfView(pov, 0);
    } catch {}
  }, [applyAutoRotate, autoRotate, pov]);

  useEffect(() => {
    applyAutoRotate(autoRotate);
  }, [autoRotate, applyAutoRotate]);

  // Re-frame to the market's default view when the instrument switches.
  useEffect(() => {
    try {
      globeRef.current?.pointOfView(pov, 600);
    } catch {}
  }, [pov]);

  const resetView = useCallback(() => {
    try {
      globeRef.current?.pointOfView(pov, 600);
    } catch {}
  }, [pov]);

  const frameScenario = useCallback(() => {
    try {
      globeRef.current?.pointOfView(frameView(points, pov), 700);
    } catch {}
  }, [points, pov]);

  const isVector = style === "vector";
  const toggleCls = (on: boolean) =>
    on ? "text-accent" : "text-ink-4 hover:text-accent";

  return (
    <div
      ref={wrapRef}
      className="relative border border-line-1 bg-surface-1 overflow-hidden"
      style={{ height: HEIGHT }}
    >
      <Globe
        ref={globeRef}
        onGlobeReady={onReady}
        width={width}
        height={HEIGHT}
        backgroundColor="rgba(0,0,0,0)"
        // ── look ──────────────────────────────────────────────────────
        globeMaterial={isVector ? vectorMaterial : undefined}
        globeImageUrl={isVector ? undefined : SAT_IMAGE}
        bumpImageUrl={isVector ? undefined : SAT_BUMP}
        showAtmosphere
        atmosphereColor={isVector ? rgba(theme.accent, 1) : "#7fb0ff"}
        atmosphereAltitude={0.16}
        showGraticules={showGrid}
        // Thin vector country outlines (vector look only) — no fill, low relief,
        // accent-tinted so they track the active palette.
        polygonsData={isVector ? countries.features : []}
        polygonCapColor={() => "rgba(0,0,0,0)"}
        polygonSideColor={() => "rgba(0,0,0,0)"}
        polygonStrokeColor={() => rgba(theme.accent, 0.7)}
        polygonAltitude={0.004}
        // ── data layers (both looks) ──────────────────────────────────
        pointsData={allPoints}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.014}
        pointRadius="size"
        pointLabel="label"
        arcsData={allArcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor="color"
        arcStroke={(d: object) =>
          (d as GlobeArc).kind === "network" ? 0.2 : 0.5
        }
        arcDashLength={(d: object) =>
          (d as GlobeArc).kind === "network" ? 1 : 0.5
        }
        arcDashGap={(d: object) =>
          (d as GlobeArc).kind === "network" ? 0 : 0.25
        }
        arcDashAnimateTime={(d: object) =>
          (d as GlobeArc).kind === "network" ? 0 : 1700
        }
        arcLabel="label"
      />

      {/* view controls + layer toggles */}
      <div className="absolute top-2 left-3 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[10px] uppercase tracking-widest">
        <button
          type="button"
          onClick={() => setAutoRotate((v) => !v)}
          aria-pressed={autoRotate}
          className={toggleCls(autoRotate)}
        >
          {autoRotate ? "Spin ⏸" : "Spin ▶"}
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={resetView}
          className="text-ink-4 hover:text-accent"
        >
          Reset
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={frameScenario}
          className="text-ink-4 hover:text-accent"
        >
          Frame
        </button>
        <span className="text-line-2">|</span>
        <button
          type="button"
          onClick={() => setShowInfra((v) => !v)}
          aria-pressed={showInfra}
          className={toggleCls(showInfra)}
        >
          Infra
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={() => setShowNetwork((v) => !v)}
          aria-pressed={showNetwork}
          className={toggleCls(showNetwork)}
        >
          Network
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={() => setShowGrid((v) => !v)}
          aria-pressed={showGrid}
          className={toggleCls(showGrid)}
        >
          Grid
        </button>
      </div>

      {/* style toggle */}
      <div className="absolute top-2 right-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
        <button
          type="button"
          onClick={() => setStyle("vector")}
          aria-pressed={isVector}
          className={isVector ? "text-accent" : "text-ink-4 hover:text-accent"}
        >
          Vector
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={() => setStyle("satellite")}
          aria-pressed={!isVector}
          className={!isVector ? "text-accent" : "text-ink-4 hover:text-accent"}
        >
          Satellite
        </button>
      </div>

      {/* legend */}
      <div className="absolute bottom-2 left-3 flex items-center gap-3 font-mono text-[9px] uppercase tracking-widest text-ink-4 pointer-events-none">
        <span>
          <span className="text-up">●</span> bullish
        </span>
        <span>
          <span className="text-down">●</span> bearish
        </span>
        {benchmarkOf(instrument) && (
          <span>
            <span style={{ color: rgba(theme.accent, 1) }}>●</span>{" "}
            {benchmarkOf(instrument)}
          </span>
        )}
      </div>
      {!hasScenarioGeography(instrument) ? (
        <div className="absolute bottom-2 right-3 font-mono text-[10px] text-ink-4 pointer-events-none">
          No scenario geography for this asset class.
        </div>
      ) : (
        arcs.length === 0 && (
          <div className="absolute bottom-2 right-3 font-mono text-[10px] text-ink-4 pointer-events-none">
            Load a scenario to trace its impact flows.
          </div>
        )
      )}
    </div>
  );
}
