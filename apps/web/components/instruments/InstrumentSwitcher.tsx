"use client";

import { useInstruments } from "@/lib/queries";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { useEffect, useRef, useState } from "react";

interface Props {
  className?: string;
}

/**
 * Compact instrument dropdown — used on pages without room for the full
 * watchlist sidebar (Chart, Signal Lab, Scenario Lab, Journal, Paper,
 * Calibration, Admin).
 */
export function InstrumentSwitcher({ className = "" }: Props) {
  const { data } = useInstruments();
  const { activeSymbol, setActiveSymbol } = useActiveInstrument();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", onDoc);
      document.addEventListener("keydown", onKey);
      return () => {
        document.removeEventListener("mousedown", onDoc);
        document.removeEventListener("keydown", onKey);
      };
    }
  }, [open]);

  const rows = data?.instruments ?? [];
  const active = rows.find((r) => r.symbol === activeSymbol);
  const label = active?.symbol ?? activeSymbol;
  const name = active?.name ?? "";

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Switch instrument"
        className="inline-flex items-center gap-2 border border-line-1 px-2.5 py-1 bg-surface-1 hover:bg-surface-2 hover:border-line-2 transition-colors"
        data-testid="instrument-switcher"
      >
        <span className="font-mono text-xs font-semibold text-ink-1">
          {label}
        </span>
        {name ? (
          <span className="text-[10px] text-ink-3 max-w-[120px] truncate">
            {name}
          </span>
        ) : null}
        <span aria-hidden="true" className="text-ink-4 text-xs">
          ▾
        </span>
      </button>
      {open ? (
        // biome-ignore lint/a11y/useFocusableInteractive: options inside are focusable buttons; the listbox container is not a tab stop by design
        <ul
          // biome-ignore lint/a11y/useSemanticElements: styled custom dropdown using the ARIA listbox pattern; native <select> cannot carry this layout
          // biome-ignore lint/a11y/noNoninteractiveElementToInteractiveRole: intentional ARIA listbox over a styled <ul>; native <select> cannot carry this layout
          role="listbox"
          aria-label="Instruments"
          className="absolute right-0 top-full mt-1 z-50 min-w-[200px] border border-line-2 bg-surface-1 shadow-xl flex flex-col"
        >
          {rows.length === 0 ? (
            <li className="px-3 py-2 text-xs text-ink-4 font-mono">
              No instruments.
            </li>
          ) : (
            rows.map((r) => {
              const isActive = r.symbol === activeSymbol;
              return (
                <li key={r.symbol}>
                  <button
                    type="button"
                    // biome-ignore lint/a11y/useSemanticElements: ARIA option inside a styled custom listbox; native <option> is not stylable here
                    role="option"
                    aria-selected={isActive}
                    onClick={() => {
                      setActiveSymbol(r.symbol);
                      setOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 flex items-baseline justify-between gap-3 border-l-4 transition-colors ${
                      isActive
                        ? "border-l-accent bg-surface-2 text-accent-bright"
                        : "border-l-transparent hover:bg-surface-2/60 hover:border-l-line-2 text-ink-2"
                    }`}
                  >
                    <span className="font-mono text-xs font-semibold">
                      {r.symbol}
                    </span>
                    <span className="text-[10px] text-ink-3 truncate max-w-[120px]">
                      {r.name}
                    </span>
                  </button>
                </li>
              );
            })
          )}
        </ul>
      ) : null}
    </div>
  );
}
