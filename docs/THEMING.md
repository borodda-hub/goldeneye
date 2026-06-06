# Theming

Global color themes for the web app. A theme is **data** (a palette object),
applied at runtime as CSS variables — built so user-authored themes (Phase 2)
slot in without rearchitecting.

## Model

- **Source of truth:** `apps/web/lib/theme/themes.ts` — each theme is a
  `Palette` (one hex per token; tokens defined in `lib/theme/palette.ts`).
- **Applied as CSS variables** on `<html>` in **RGB-channel-triplet** form
  (`--surface-1: 19 19 17`). Tailwind tokens resolve via
  `rgb(var(--token) / <alpha-value>)`, so opacity utilities (`bg-surface-1/90`)
  keep working.
- **Page chrome** uses the Tailwind tokens / CSS vars. **Charts** (which take raw
  color strings) read the active palette through `useThemeColors()`
  (`lib/theme/useThemeColors.ts`), which returns the legacy `lib/colors.ts` shape.

## Runtime flow

- `ThemeProvider` (`lib/theme/ThemeProvider.tsx`, mounted in `app/(app)/layout.tsx`)
  holds the active theme id, persists it to `localStorage["goldeneye:theme"]`,
  syncs across tabs, and reflects it to `<html data-theme>`.
- Built-in palettes are emitted as `:root` (default `goldeneye`) and
  `[data-theme="…"]` blocks in `app/globals.css`. The default omits the attribute
  so SSR markup and first paint are correct with no flash.
- A blocking inline script in `app/layout.tsx` sets `data-theme` from
  localStorage before first paint, so a non-default theme doesn't flash.
- The chart's own Appearance system (`lib/chart/chartStyle.ts`) keeps working;
  `themedChartStyle()` makes the **default "dark"** appearance inherit the global
  theme, while an explicitly chosen `light`/`gold`/`custom` appearance still wins.

## Built-in themes

`goldeneye` (default), `slate`, `phosphor`, `ember`, `onyx`. Switch via the
palette control in the TopBar (`components/ThemeSwitcher.tsx`).

## Add a theme

1. Add a `Palette` to `lib/theme/themes.ts` and register it in `BUILTIN_THEMES`.
2. Add the matching CSS block to `app/globals.css` (`[data-theme="<id>"]`, triplet
   form — `hexToTriplet` from `lib/theme/palette.ts` gives the values).
3. The drift test in `lib/theme/__tests__/palette.test.ts` enforces that the CSS
   block matches the palette; run `pnpm vitest run lib/theme`.

## Constraints

- Tailwind tokens must stay in the `rgb(var(--token) / <alpha-value>)` form.
- `goldeneye` must remain byte-identical to `lib/colors.ts` (asserted by test) so
  existing users see no change unless they switch.
- Keep themes **dark** for now — light mode needs the grain/glow/shadow layers
  re-tuned and is out of scope.

## Out of scope (Phase 2/3)

User-authored themes: a seed-and-derive editor (pick ~6 seeds → derive the rest),
contrast/a11y guards, export/import, and backend storage + sharing. The palette
model above is the shape those will produce; nothing here needs to change to add
them.
