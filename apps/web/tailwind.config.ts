import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./stories/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
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
