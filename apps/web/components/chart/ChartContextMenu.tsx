"use client";

import { useEffect } from "react";

export interface ChartMenuItem {
  label: string;
  onClick: () => void;
}

interface Props {
  x: number;
  y: number;
  items: ChartMenuItem[];
  onClose: () => void;
}

/**
 * Right-click menu for the chart. Opened from a `contextmenu` handler with the
 * cursor position; closes on any click, another right-click, or Escape.
 */
export function ChartContextMenu({ x, y, items, onClose }: Props) {
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Defer so the opening right-click doesn't immediately re-close it.
    const id = window.setTimeout(() => {
      window.addEventListener("click", close);
      window.addEventListener("contextmenu", close);
      window.addEventListener("keydown", onKey);
    }, 0);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("click", close);
      window.removeEventListener("contextmenu", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  // Nudge the menu in from the edges so it doesn't clip the viewport.
  const left = Math.min(x, (globalThis.innerWidth ?? x) - 180);
  const top = Math.min(
    y,
    (globalThis.innerHeight ?? y) - items.length * 32 - 16,
  );

  return (
    <div
      role="menu"
      aria-label="Chart actions"
      className="fixed z-[60] min-w-[160px] rounded-md border border-line-2 bg-surface-1 py-1 shadow-2xl"
      style={{ left, top }}
    >
      {items.map((it) => (
        <button
          key={it.label}
          type="button"
          role="menuitem"
          onClick={() => {
            it.onClick();
            onClose();
          }}
          className="block w-full px-3 py-1.5 text-left font-mono text-[11px] text-ink-2 hover:bg-surface-2 hover:text-ink-1"
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
