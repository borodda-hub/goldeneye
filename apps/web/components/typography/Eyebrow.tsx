import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Optional className for layout overrides (margin, alignment). */
  className?: string;
}

/**
 * Mono uppercase label with a leading 18px gold rule.
 * Used as a section-introducer above DisplayHeading, or above any major panel.
 */
export function Eyebrow({ children, className = "" }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-[0.28em] text-accent ${className}`}
    >
      <span
        aria-hidden="true"
        className="inline-block w-[18px] h-px bg-accent"
      />
      {children}
    </span>
  );
}
