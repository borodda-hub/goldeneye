"use client";

import { colors as DEFAULT_COLORS } from "@/lib/colors";
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ThemeColors } from "./palette";
import { paletteToColors } from "./palette";
import {
  BUILTIN_THEMES,
  DEFAULT_THEME_ID,
  THEMES_BY_ID,
  type ThemeDef,
  getTheme,
} from "./themes";

const STORAGE_KEY = "goldeneye:theme";

interface ThemeContextValue {
  themeId: string;
  setThemeId: (id: string) => void;
  themes: ThemeDef[];
  /** Active palette as chart-library color strings (legacy `colors` shape). */
  colors: ThemeColors;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Reflect the active theme to <html data-theme>; the default omits the attribute
 *  so the `:root` block (and SSR markup) applies with no flash. */
function applyThemeAttr(id: string): void {
  if (typeof document === "undefined") return;
  const el = document.documentElement;
  if (id === DEFAULT_THEME_ID) el.removeAttribute("data-theme");
  else el.setAttribute("data-theme", id);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // SSR-safe: render the default first, hydrate the stored choice in an effect
  // (the no-flash head script already set data-theme for first paint).
  const [themeId, setThemeIdState] = useState<string>(DEFAULT_THEME_ID);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && THEMES_BY_ID[stored]) setThemeIdState(stored);
    } catch {
      // localStorage unavailable — keep default.
    }
  }, []);

  // Cross-tab sync (mirrors lib/useChartColor.ts).
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key !== STORAGE_KEY) return;
      const v = e.newValue;
      if (v && THEMES_BY_ID[v]) setThemeIdState(v);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    applyThemeAttr(themeId);
  }, [themeId]);

  const setThemeId = useCallback((id: string) => {
    if (!THEMES_BY_ID[id]) return;
    setThemeIdState(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // ignore — UI still updates in-memory.
    }
  }, []);

  const value = useMemo<ThemeContextValue>(() => {
    const palette = getTheme(themeId).palette;
    return {
      themeId,
      setThemeId,
      themes: BUILTIN_THEMES,
      colors: paletteToColors(palette),
    };
  }, [themeId, setThemeId]);

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}

/** Active theme's chart colors, with a safe fallback to the default palette for
 *  any consumer rendered outside the provider (e.g. the marketing page). */
export function useThemeColors(): ThemeColors {
  const ctx = useContext(ThemeContext);
  return ctx ? ctx.colors : DEFAULT_COLORS;
}
