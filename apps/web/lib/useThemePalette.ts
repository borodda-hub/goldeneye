"use client";

import { useEffect, useState } from "react";

/** Theme tokens (CSS custom properties) the impact globe paints with. Each is an
 *  "R G B" triplet in globals.css; we resolve them to usable color strings and
 *  re-resolve whenever the active palette (<html data-theme>) changes. */
export interface ThemePalette {
  accent: string;
  accentBright: string;
  up: string;
  down: string;
}

const VARS: Record<keyof ThemePalette, string> = {
  accent: "--accent",
  accentBright: "--accent-bright",
  up: "--up",
  down: "--down",
};

const FALLBACK: ThemePalette = {
  accent: "201 163 92",
  accentBright: "224 188 116",
  up: "65 209 139",
  down: "240 97 109",
};

function readPalette(): ThemePalette {
  if (typeof window === "undefined") return FALLBACK;
  const cs = getComputedStyle(document.documentElement);
  const read = (v: string, fb: string) => cs.getPropertyValue(v).trim() || fb;
  return {
    accent: read(VARS.accent, FALLBACK.accent),
    accentBright: read(VARS.accentBright, FALLBACK.accentBright),
    up: read(VARS.up, FALLBACK.up),
    down: read(VARS.down, FALLBACK.down),
  };
}

/** Read the active theme palette, refreshing on every palette switch. */
export function useThemePalette(): ThemePalette {
  const [palette, setPalette] = useState<ThemePalette>(FALLBACK);

  useEffect(() => {
    setPalette(readPalette());
    const obs = new MutationObserver(() => setPalette(readPalette()));
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => obs.disconnect();
  }, []);

  return palette;
}

/** "R G B" triplet → "rgba(R, G, B, a)" — comma form, since three.js / three-globe
 *  do not parse the modern space-slash `rgb(R G B / a)` syntax. */
export function rgba(triplet: string, alpha: number): string {
  const [r, g, b] = triplet.trim().split(/[\s,]+/);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
