/**
 * Theme palette model — the single source of truth for app colors.
 *
 * A theme (built-in or, later, user-authored) is one {@link Palette}: a hex value
 * per design token. At runtime the active palette is injected onto <html> as CSS
 * custom properties in **RGB-channel-triplet** form (`"19 19 17"`) so Tailwind's
 * opacity utilities keep working via `rgb(var(--token) / <alpha-value>)`.
 *
 * Charts (which take raw color strings) read the same palette through
 * `useThemeColors()`, which maps a Palette to the legacy `lib/colors.ts` shape.
 */

/** Canonical design tokens (kebab names == the CSS variables and Tailwind keys). */
export const TOKENS = [
  "surface-0",
  "surface-1",
  "surface-2",
  "surface-3",
  "line-1",
  "line-2",
  "ink-1",
  "ink-1-soft",
  "ink-2",
  "ink-3",
  "ink-4",
  "up",
  "down",
  "flat",
  "up-soft",
  "down-soft",
  "accent",
  "accent-bright",
  "accent-deep",
  "accent-soft",
  "conf-low",
  "conf-medium",
  "conf-high",
  "cyan",
  "violet",
] as const;

export type Token = (typeof TOKENS)[number];

/** A complete theme: one hex value (`#rrggbb`) per token. */
export type Palette = Record<Token, string>;

/** The raw-string color shape consumed by the chart libraries (camelCase keys,
 *  matching the legacy `lib/colors.ts` export). */
export interface ThemeColors {
  bg: string;
  surface1: string;
  surface2: string;
  surface3: string;
  line1: string;
  line2: string;
  ink1: string;
  ink1Soft: string;
  ink2: string;
  ink3: string;
  ink4: string;
  up: string;
  down: string;
  flat: string;
  upSoft: string;
  downSoft: string;
  accent: string;
  accentBright: string;
  accentDeep: string;
  accentSoft: string;
  amber: string;
  cyan: string;
  violet: string;
}

/** `#rrggbb` (or `#rgb`) → `"r g b"` channel triplet for CSS `rgb(var() / a)`. */
export function hexToTriplet(hex: string): string {
  const h = hex.replace("#", "").trim();
  const full =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  const r = Number.parseInt(full.slice(0, 2), 16);
  const g = Number.parseInt(full.slice(2, 4), 16);
  const b = Number.parseInt(full.slice(4, 6), 16);
  return `${r} ${g} ${b}`;
}

/** `"r g b"` channel triplet → `#rrggbb`. Inverse of {@link hexToTriplet}. */
export function tripletToHex(triplet: string): string {
  const [r, g, b] = triplet.trim().split(/\s+/).map(Number);
  const h = (x: number) =>
    Math.max(0, Math.min(255, x)).toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

/** Inject a palette onto an element as `--token` CSS variables (triplet form). */
export function applyPalette(el: HTMLElement, palette: Palette): void {
  for (const token of TOKENS) {
    el.style.setProperty(`--${token}`, hexToTriplet(palette[token]));
  }
}

/** Map a Palette to the chart libraries' camelCase color shape. */
export function paletteToColors(p: Palette): ThemeColors {
  return {
    bg: p["surface-0"],
    surface1: p["surface-1"],
    surface2: p["surface-2"],
    surface3: p["surface-3"],
    line1: p["line-1"],
    line2: p["line-2"],
    ink1: p["ink-1"],
    ink1Soft: p["ink-1-soft"],
    ink2: p["ink-2"],
    ink3: p["ink-3"],
    ink4: p["ink-4"],
    up: p.up,
    down: p.down,
    flat: p.flat,
    upSoft: p["up-soft"],
    downSoft: p["down-soft"],
    accent: p.accent,
    accentBright: p["accent-bright"],
    accentDeep: p["accent-deep"],
    accentSoft: p["accent-soft"],
    amber: p["conf-low"],
    cyan: p.cyan,
    violet: p.violet,
  };
}
