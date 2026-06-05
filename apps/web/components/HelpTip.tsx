"use client";

import { HELP, type HelpKey } from "@/lib/helpText";
import { useId, useState } from "react";

interface Props {
  /** Glossary key — the usual API. Resolves to text from lib/helpText. */
  k?: HelpKey;
  /** Inline override when the text isn't in the glossary. */
  text?: string;
  /** Horizontal anchor of the popup relative to the icon. Use "right" when the
   *  header sits near the right edge of its container. */
  align?: "left" | "right";
  /** Extra classes for the inline wrapper (e.g. spacing tweaks). */
  className?: string;
}

/**
 * A small gold "ⓘ" affordance that reveals a one-line explanation on hover or
 * keyboard focus. Built for feature headers so first-time users can decode the
 * jargon. No external dependency — pure hover/focus state, Escape to dismiss.
 *
 * The popup resets the typographic context (headers are uppercase mono) back to
 * sentence-case sans so the help text stays readable.
 */
export function HelpTip({ k, text, align = "left", className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const body = text ?? (k ? HELP[k] : "");
  return (
    <span
      className={`relative inline-flex items-center align-middle ${className}`}
    >
      <button
        type="button"
        aria-label="What is this?"
        aria-describedby={open ? id : undefined}
        className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-accent/40 text-accent/70 text-[9px] font-semibold normal-case leading-none cursor-help transition-colors hover:border-accent/80 hover:text-accent focus:text-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-accent/60"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          id={id}
          className={`absolute top-full z-50 mt-1.5 w-60 rounded-md border border-line-1 bg-surface-1 px-3 py-2 text-[11px] font-sans normal-case leading-relaxed tracking-normal text-cyan shadow-lg shadow-black/40 ${
            align === "right" ? "right-0" : "left-0"
          }`}
        >
          {body}
        </span>
      )}
    </span>
  );
}
