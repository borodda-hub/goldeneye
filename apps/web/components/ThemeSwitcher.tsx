"use client";

import { useTheme } from "@/lib/theme/ThemeProvider";
import { Check, Palette } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/** TopBar control to switch the global color theme. Shows a 3-swatch preview
 *  (surface / accent / up) per theme; persists via the ThemeProvider. */
export function ThemeSwitcher() {
  const { themeId, setThemeId, themes } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Color theme"
        title="Color theme"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center text-ink-3 transition-colors hover:text-accent"
      >
        <Palette size={14} strokeWidth={1.5} aria-hidden="true" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-44 rounded-sm border border-line-1 bg-surface-1 py-1 shadow-xl"
        >
          <div className="px-3 py-1 font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Theme
          </div>
          {themes.map((t) => {
            const active = t.id === themeId;
            const swatches = [
              t.palette["surface-1"],
              t.palette.accent,
              t.palette.up,
            ];
            return (
              <button
                key={t.id}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                onClick={() => {
                  setThemeId(t.id);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2.5 px-3 py-1.5 text-[12px] transition-colors ${
                  active
                    ? "text-accent"
                    : "text-ink-2 hover:bg-surface-2 hover:text-ink-1"
                }`}
              >
                <span className="flex shrink-0 gap-0.5">
                  {swatches.map((c, i) => (
                    <span
                      key={`${t.id}-${i}`}
                      className="h-3 w-3 rounded-[2px] border border-black/30"
                      style={{ background: c }}
                    />
                  ))}
                </span>
                <span className="flex-1 text-left">{t.name}</span>
                {active && (
                  <Check size={12} strokeWidth={2} aria-hidden="true" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
