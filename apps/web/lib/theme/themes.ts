import type { Palette } from "./palette";

/**
 * Built-in dark themes. `goldeneye` is the default and its values are identical
 * to the original hardcoded palette (`lib/colors.ts` / `tailwind.config.ts`), so
 * existing users see no change unless they switch. The alternates keep the same
 * surface/ink structure and shift the accent (and neutral temperature).
 *
 * Each is a complete {@link Palette}; a unit test asserts every token is present
 * and that `goldeneye` matches the legacy `colors` export.
 */

// The original palette — must stay byte-identical to lib/colors.ts.
const goldeneye: Palette = {
  "surface-0": "#0a0a09",
  "surface-1": "#131311",
  "surface-2": "#1a1a17",
  "surface-3": "#222220",
  "line-1": "#2a2a26",
  "line-2": "#3a3a34",
  "ink-1": "#efece3",
  "ink-1-soft": "#d7d4cc",
  "ink-2": "#b4afa4",
  "ink-3": "#979281",
  "ink-4": "#726d62",
  up: "#6dd58c",
  down: "#e87575",
  flat: "#88857c",
  "up-soft": "#0e1a12",
  "down-soft": "#1c0e0e",
  accent: "#c9a35c",
  "accent-bright": "#e8c074",
  "accent-deep": "#8a6f3a",
  "accent-soft": "#1a140a",
  "conf-low": "#f0b429",
  "conf-medium": "#e8c074",
  "conf-high": "#6dd58c",
  cyan: "#7dd3e0",
  violet: "#a89cdb",
};

// Cool steel surfaces, cyan accent.
const slate: Palette = {
  "surface-0": "#0a0b0d",
  "surface-1": "#121519",
  "surface-2": "#181c22",
  "surface-3": "#21262e",
  "line-1": "#272d35",
  "line-2": "#38404a",
  "ink-1": "#e6ebf0",
  "ink-1-soft": "#cfd6dd",
  "ink-2": "#a6b0bb",
  "ink-3": "#7f8a96",
  "ink-4": "#5c6670",
  up: "#5ec8a0",
  down: "#e3737f",
  flat: "#808a94",
  "up-soft": "#0c1a17",
  "down-soft": "#1c0f12",
  accent: "#5fb3c9",
  "accent-bright": "#8fd6e6",
  "accent-deep": "#3a7d8f",
  "accent-soft": "#0c171b",
  "conf-low": "#e0b341",
  "conf-medium": "#8fd6e6",
  "conf-high": "#5ec8a0",
  cyan: "#7dd3e0",
  violet: "#9fb0e0",
};

// Near-black with a green CRT-terminal accent.
const phosphor: Palette = {
  "surface-0": "#080a08",
  "surface-1": "#0f130f",
  "surface-2": "#141914",
  "surface-3": "#1c231c",
  "line-1": "#232a23",
  "line-2": "#323b32",
  "ink-1": "#e4f0e4",
  "ink-1-soft": "#cdd9cd",
  "ink-2": "#a3b3a3",
  "ink-3": "#7d8c7d",
  "ink-4": "#5a665a",
  up: "#5fd07a",
  down: "#e07575",
  flat: "#859485",
  "up-soft": "#0c1a0f",
  "down-soft": "#1c0e0e",
  accent: "#4fd06a",
  "accent-bright": "#82e89a",
  "accent-deep": "#2f8a44",
  "accent-soft": "#0c1a0f",
  "conf-low": "#e0c341",
  "conf-medium": "#82e89a",
  "conf-high": "#5fd07a",
  cyan: "#6fd0c0",
  violet: "#9fb0d0",
};

// Warm charcoal, copper/amber accent, warmer text.
const ember: Palette = {
  "surface-0": "#0c0a08",
  "surface-1": "#161310",
  "surface-2": "#1d1814",
  "surface-3": "#26201b",
  "line-1": "#2e2620",
  "line-2": "#41352c",
  "ink-1": "#f0e9e0",
  "ink-1-soft": "#ddd2c6",
  "ink-2": "#b8aa9a",
  "ink-3": "#978676",
  "ink-4": "#6e5f50",
  up: "#7ccf7a",
  down: "#e8745f",
  flat: "#8c8378",
  "up-soft": "#121a0e",
  "down-soft": "#1f0f0b",
  accent: "#cf8a4a",
  "accent-bright": "#edb06a",
  "accent-deep": "#8a5a2f",
  "accent-soft": "#1c140c",
  "conf-low": "#f0a52e",
  "conf-medium": "#edb06a",
  "conf-high": "#7ccf7a",
  cyan: "#7dc8c0",
  violet: "#b09cd0",
};

// Near-monochrome neutral greys, restrained platinum accent.
const onyx: Palette = {
  "surface-0": "#0a0a0a",
  "surface-1": "#141414",
  "surface-2": "#1b1b1b",
  "surface-3": "#242424",
  "line-1": "#2b2b2b",
  "line-2": "#3b3b3b",
  "ink-1": "#ededed",
  "ink-1-soft": "#d4d4d4",
  "ink-2": "#ababab",
  "ink-3": "#8a8a8a",
  "ink-4": "#636363",
  up: "#79c98f",
  down: "#d9787c",
  flat: "#888888",
  "up-soft": "#121a14",
  "down-soft": "#1a1011",
  accent: "#c8c2b4",
  "accent-bright": "#e0dccf",
  "accent-deep": "#8a8578",
  "accent-soft": "#1a1916",
  "conf-low": "#d9b24a",
  "conf-medium": "#e0dccf",
  "conf-high": "#79c98f",
  cyan: "#84c4cc",
  violet: "#a9a3c0",
};

// Deep indigo / blue-violet surfaces, periwinkle accent.
const indigo: Palette = {
  "surface-0": "#08080f",
  "surface-1": "#0f0f1a",
  "surface-2": "#151424",
  "surface-3": "#1d1c30",
  "line-1": "#242338",
  "line-2": "#34324f",
  "ink-1": "#e8e7f2",
  "ink-1-soft": "#d0cfe0",
  "ink-2": "#a5a3c0",
  "ink-3": "#7d7b9c",
  "ink-4": "#5a5878",
  up: "#6dd58c",
  down: "#e87575",
  flat: "#8884a0",
  "up-soft": "#0e1a12",
  "down-soft": "#1c0e0e",
  accent: "#7d7ff0",
  "accent-bright": "#a8aaff",
  "accent-deep": "#4f50b0",
  "accent-soft": "#12122a",
  "conf-low": "#e0b341",
  "conf-medium": "#a8aaff",
  "conf-high": "#6dd58c",
  cyan: "#7dd3e0",
  violet: "#a89cdb",
};

// Warm plum-charcoal surfaces, dusty rose accent.
const mauve: Palette = {
  "surface-0": "#0d0a0c",
  "surface-1": "#171115",
  "surface-2": "#1e171b",
  "surface-3": "#281f24",
  "line-1": "#2f252b",
  "line-2": "#443642",
  "ink-1": "#f0e8ee",
  "ink-1-soft": "#ddd0d8",
  "ink-2": "#bba8b4",
  "ink-3": "#998693",
  "ink-4": "#6f5e68",
  up: "#7ccf9a",
  down: "#e8748f",
  flat: "#8c8088",
  "up-soft": "#121a14",
  "down-soft": "#1f0e14",
  accent: "#cf7da0",
  "accent-bright": "#e8a0bd",
  "accent-deep": "#8a4f68",
  "accent-soft": "#1c1015",
  "conf-low": "#e0a84a",
  "conf-medium": "#e8a0bd",
  "conf-high": "#7ccf9a",
  cyan: "#7dc8d0",
  violet: "#b09cd0",
};

// Near-black teal surfaces, bright aqua accent.
const abyss: Palette = {
  "surface-0": "#050b0b",
  "surface-1": "#0a1414",
  "surface-2": "#0f1c1c",
  "surface-3": "#152727",
  "line-1": "#1b2e2e",
  "line-2": "#294040",
  "ink-1": "#e0f0ef",
  "ink-1-soft": "#c8dcdb",
  "ink-2": "#9db8b6",
  "ink-3": "#769190",
  "ink-4": "#54706f",
  up: "#4fd0a0",
  down: "#e87580",
  flat: "#7e9492",
  "up-soft": "#0a1a16",
  "down-soft": "#1c0e10",
  accent: "#3fd0c8",
  "accent-bright": "#6ee8e0",
  "accent-deep": "#248a84",
  "accent-soft": "#0a1c1b",
  "conf-low": "#e0c341",
  "conf-medium": "#6ee8e0",
  "conf-high": "#4fd0a0",
  cyan: "#6fd0d8",
  violet: "#9fb0d0",
};

// Nord-inspired: muted cool blue-grey surfaces, frost-blue accent, aurora
// up/down. Deepened below true Nord to sit in the app's dark aesthetic.
const nord: Palette = {
  "surface-0": "#14181f",
  "surface-1": "#1c212a",
  "surface-2": "#232934",
  "surface-3": "#2e3440",
  "line-1": "#3b4252",
  "line-2": "#4c566a",
  "ink-1": "#eceff4",
  "ink-1-soft": "#e5e9f0",
  "ink-2": "#d8dee9",
  "ink-3": "#9aa5b8",
  "ink-4": "#6b7488",
  up: "#a3be8c",
  down: "#bf616a",
  flat: "#8893a5",
  "up-soft": "#141c14",
  "down-soft": "#1c1012",
  accent: "#88c0d0",
  "accent-bright": "#8fbcbb",
  "accent-deep": "#5e81ac",
  "accent-soft": "#141c22",
  "conf-low": "#ebcb8b",
  "conf-medium": "#8fbcbb",
  "conf-high": "#a3be8c",
  cyan: "#88c0d0",
  violet: "#b48ead",
};

export interface ThemeDef {
  id: string;
  name: string;
  palette: Palette;
}

export const DEFAULT_THEME_ID = "goldeneye";

export const BUILTIN_THEMES: ThemeDef[] = [
  { id: "goldeneye", name: "Goldeneye", palette: goldeneye },
  { id: "slate", name: "Slate", palette: slate },
  { id: "phosphor", name: "Phosphor", palette: phosphor },
  { id: "ember", name: "Ember", palette: ember },
  { id: "onyx", name: "Onyx", palette: onyx },
  { id: "indigo", name: "Indigo", palette: indigo },
  { id: "mauve", name: "Mauve", palette: mauve },
  { id: "abyss", name: "Abyss", palette: abyss },
  { id: "nord", name: "Nord", palette: nord },
];

export const THEMES_BY_ID: Record<string, ThemeDef> = Object.fromEntries(
  BUILTIN_THEMES.map((t) => [t.id, t]),
);

export function getTheme(id: string | null | undefined): ThemeDef {
  return (id && THEMES_BY_ID[id]) || THEMES_BY_ID[DEFAULT_THEME_ID];
}
