"use client";

import type { Shock } from "@/app/(app)/scenarios/types";
import { buildGlobeLayers } from "@/lib/scenarioGeo";
import { rgba, useThemePalette } from "@/lib/useThemePalette";
import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";

// Bundled same-origin (the unpkg dataset URL 404s) so outlines always load.
const COUNTRIES_URL = "/geo/countries-110m.geojson";
// Standard satellite imagery (NASA blue-marble) + topology bump for relief.
const SAT_IMAGE =
  "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";
const SAT_BUMP = "https://unpkg.com/three-globe/example/img/earth-topology.png";
const HEIGHT = 440;

type GlobeStyle = "vector" | "satellite";

/**
 * The scenario impact globe. Renders a scenario's geography — glowing loci and
 * animated arcs colored by each shock's directional lean — in one of two looks:
 * "vector" (soft country outlines on a dark sphere, on-brand) or "satellite"
 * (standard NASA blue-marble imagery). Client-only (parent imports it ssr:false).
 */
export function ScenarioGlobe({ shocks }: { shocks: Shock[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [width, setWidth] = useState(640);
  const [style, setStyle] = useState<GlobeStyle>("vector");
  const [countries, setCountries] = useState<{ features: object[] }>({
    features: [],
  });

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
    () => buildGlobeLayers(shocks, leanPalette),
    [shocks, leanPalette],
  );

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

  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    try {
      const controls = g.controls() as {
        autoRotate: boolean;
        autoRotateSpeed: number;
      };
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.5;
      g.pointOfView({ lat: 38, lng: -45, altitude: 2.0 }, 0);
    } catch {}
  }, []);

  const isVector = style === "vector";

  return (
    <div
      ref={wrapRef}
      className="relative border border-line-1 bg-surface-1 overflow-hidden"
      style={{ height: HEIGHT }}
    >
      <Globe
        ref={globeRef}
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
        // Thin vector country outlines (vector look only) — no fill, low relief,
        // accent-tinted so they track the active palette.
        polygonsData={isVector ? countries.features : []}
        polygonCapColor={() => "rgba(0,0,0,0)"}
        polygonSideColor={() => "rgba(0,0,0,0)"}
        polygonStrokeColor={() => rgba(theme.accent, 0.7)}
        polygonAltitude={0.004}
        // ── data layers (both looks) ──────────────────────────────────
        pointsData={points}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.014}
        pointRadius="size"
        pointLabel="label"
        arcsData={arcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor="color"
        arcStroke={0.55}
        arcDashLength={0.5}
        arcDashGap={0.25}
        arcDashAnimateTime={1700}
        arcLabel="label"
      />

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
        <span>
          <span style={{ color: rgba(theme.accent, 1) }}>●</span> Henry Hub
        </span>
      </div>
      {arcs.length === 0 && (
        <div className="absolute bottom-2 right-3 font-mono text-[10px] text-ink-4 pointer-events-none">
          Load a scenario to trace its impact flows.
        </div>
      )}
    </div>
  );
}
