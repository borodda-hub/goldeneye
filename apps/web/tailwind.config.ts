import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./stories/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // Tokens resolve to the active theme's CSS variables (defined in
      // app/globals.css; switched via <html data-theme>). The RGB-triplet form
      // keeps Tailwind opacity utilities working, e.g. `bg-surface-1/90`.
      colors: {
        "surface-0": "rgb(var(--surface-0) / <alpha-value>)",
        "surface-1": "rgb(var(--surface-1) / <alpha-value>)",
        "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
        "surface-3": "rgb(var(--surface-3) / <alpha-value>)",
        "line-1": "rgb(var(--line-1) / <alpha-value>)",
        "line-2": "rgb(var(--line-2) / <alpha-value>)",
        "ink-1": "rgb(var(--ink-1) / <alpha-value>)",
        "ink-1-soft": "rgb(var(--ink-1-soft) / <alpha-value>)",
        "ink-2": "rgb(var(--ink-2) / <alpha-value>)",
        "ink-3": "rgb(var(--ink-3) / <alpha-value>)",
        "ink-4": "rgb(var(--ink-4) / <alpha-value>)",
        up: "rgb(var(--up) / <alpha-value>)",
        down: "rgb(var(--down) / <alpha-value>)",
        flat: "rgb(var(--flat) / <alpha-value>)",
        "up-soft": "rgb(var(--up-soft) / <alpha-value>)",
        "down-soft": "rgb(var(--down-soft) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        "accent-bright": "rgb(var(--accent-bright) / <alpha-value>)",
        "accent-deep": "rgb(var(--accent-deep) / <alpha-value>)",
        "accent-soft": "rgb(var(--accent-soft) / <alpha-value>)",
        "conf-low": "rgb(var(--conf-low) / <alpha-value>)",
        "conf-medium": "rgb(var(--conf-medium) / <alpha-value>)",
        "conf-high": "rgb(var(--conf-high) / <alpha-value>)",
        cyan: "rgb(var(--cyan) / <alpha-value>)",
        violet: "rgb(var(--violet) / <alpha-value>)",
      },
      fontFamily: {
        serif: ["Fraunces", "ui-serif", "Georgia", "serif"],
        sans: [
          "Hanken Grotesk",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        // Override Tailwind's defaults to match the Goldeneye deck's wider mono-label tracking.
        // Default `widest` was 0.1em — too tight for uppercase mono labels in this aesthetic.
        widest: "0.22em",
        eyebrow: "0.28em",
        label: "0.18em",
      },
    },
  },
  plugins: [],
};

export default config;
