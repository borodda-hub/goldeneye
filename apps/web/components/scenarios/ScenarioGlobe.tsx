"use client";

import type { Shock } from "@/app/(app)/scenarios/types";
import { buildGlobeLayers } from "@/lib/scenarioGeo";
import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";

const COUNTRIES_URL =
  "https://unpkg.com/three-globe/example/datasets/ne_110m_admin_0_countries.geojson";
const HEIGHT = 440;

/**
 * Prototype: a dark, on-brand globe that renders the *geography* of a scenario —
 * glowing loci (terminals/basins/regions/Henry Hub) and animated arcs colored by
 * each shock's directional lean. Client-only (parent imports it ssr:false).
 */
export function ScenarioGlobe({ shocks }: { shocks: Shock[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [width, setWidth] = useState(640);
  const [countries, setCountries] = useState<{ features: object[] }>({
    features: [],
  });

  const { points, arcs } = useMemo(() => buildGlobeLayers(shocks), [shocks]);

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
      .catch(() => {
        /* offline — globe still shows points/arcs over a bare sphere */
      });
  }, []);

  const globeMaterial = useMemo(
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
      controls.autoRotateSpeed = 0.55;
      // Centre on the Atlantic so the US gas system + Europe are both in frame.
      g.pointOfView({ lat: 38, lng: -45, altitude: 2.1 }, 0);
    } catch {
      /* controls not ready yet */
    }
  }, []);

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
        globeMaterial={globeMaterial}
        showAtmosphere
        atmosphereColor="#c9a35c"
        atmosphereAltitude={0.16}
        hexPolygonsData={countries.features}
        hexPolygonResolution={3}
        hexPolygonMargin={0.45}
        hexPolygonAltitude={0.005}
        hexPolygonColor={() => "rgba(201,163,92,0.22)"}
        pointsData={points}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.012}
        pointRadius="size"
        pointLabel="label"
        arcsData={arcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor="color"
        arcStroke={0.5}
        arcDashLength={0.5}
        arcDashGap={0.25}
        arcDashAnimateTime={1800}
        arcLabel="label"
      />

      {/* legend / hint overlay */}
      <div className="absolute bottom-2 left-3 flex items-center gap-3 font-mono text-[9px] uppercase tracking-widest text-ink-4 pointer-events-none">
        <span>
          <span className="text-up">●</span> bullish
        </span>
        <span>
          <span className="text-down">●</span> bearish
        </span>
        <span>
          <span style={{ color: "#c9a35c" }}>●</span> Henry Hub
        </span>
      </div>
      {arcs.length === 0 && (
        <div className="absolute top-2 left-3 font-mono text-[10px] text-ink-4 pointer-events-none">
          Load a scenario to trace its impact flows.
        </div>
      )}
    </div>
  );
}
