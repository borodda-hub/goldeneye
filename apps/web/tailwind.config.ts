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
        "surface-0": "#0a0d12",
        "surface-1": "#0f1319",
        "surface-2": "#161b24",
        "surface-3": "#1d2330",
        "line-1": "#2a313e",
        "line-2": "#3a4150",
        "ink-1": "#e6ebf2",
        "ink-2": "#a7b0bf",
        "ink-3": "#6b7589",
        "ink-4": "#4a5364",
        up: "#34d399",
        down: "#f87171",
        flat: "#94a3b8",
        "up-soft": "#0d2820",
        "down-soft": "#2c1416",
        accent: "#7dd3fc",
        "accent-soft": "#0c2230",
        "conf-low": "#f59e0b",
        "conf-medium": "#fbbf24",
        "conf-high": "#34d399",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
