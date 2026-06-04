"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "goldeneye:chart-color";

export const CHART_COLOR_OPTIONS = [
  { key: "gold", label: "Gold", stroke: "#c9a35c", fill: "#1a140a" },
  { key: "cyan", label: "Cyan", stroke: "#7dd3e0", fill: "#0a1719" },
  { key: "violet", label: "Violet", stroke: "#a89cdb", fill: "#15131e" },
  { key: "green", label: "Green", stroke: "#6dd58c", fill: "#0e1a12" },
  { key: "amber", label: "Amber", stroke: "#f0b429", fill: "#1a1306" },
  { key: "cream", label: "Cream", stroke: "#efece3", fill: "#1c1b18" },
] as const;

export type ChartColorKey = (typeof CHART_COLOR_OPTIONS)[number]["key"];
export type ChartColorOption = (typeof CHART_COLOR_OPTIONS)[number];

const KEYS = CHART_COLOR_OPTIONS.map((o) => o.key) as readonly string[];

function isValid(v: string | null): v is ChartColorKey {
  return v !== null && KEYS.includes(v);
}

export function useChartColor(): [
  ChartColorOption,
  (key: ChartColorKey) => void,
] {
  // Default to the first option (gold). Reading localStorage during SSR would
  // hydration-mismatch; defer it to an effect.
  const [key, setKey] = useState<ChartColorKey>(CHART_COLOR_OPTIONS[0].key);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (isValid(stored)) {
        setKey(stored);
      }
    } catch {
      // localStorage unavailable (private mode, SSR) — keep default.
    }
  }, []);

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key !== STORAGE_KEY) return;
      if (isValid(e.newValue)) {
        setKey(e.newValue);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function update(next: ChartColorKey) {
    setKey(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore — UI still updates in-memory.
    }
  }

  const option =
    CHART_COLOR_OPTIONS.find((o) => o.key === key) ?? CHART_COLOR_OPTIONS[0];
  return [option, update];
}
