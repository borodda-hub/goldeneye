"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  value: number;
  precision?: number;
  prefix?: string;
  suffix?: string;
  /** Render a leading +/- and the absolute value (for P&L-style figures). */
  signed?: boolean;
  durationMs?: number;
  className?: string;
}

function prefersReduced(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Animates a number from its previous value to the next over `durationMs`
 * (easeOutQuad), via requestAnimationFrame. Used for hero stats so a fresh
 * figure rolls into place instead of snapping. Honors prefers-reduced-motion.
 */
export function CountUp({
  value,
  precision = 0,
  prefix = "",
  suffix = "",
  signed = false,
  durationMs = 650,
  className,
}: Props) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);

  useEffect(() => {
    const from = fromRef.current;
    const to = value;
    if (from === to) return;
    if (prefersReduced()) {
      setDisplay(to);
      fromRef.current = to;
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - (1 - t) * (1 - t);
      setDisplay(from + (to - from) * eased);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        fromRef.current = to;
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs]);

  const sign = signed ? (display < 0 ? "-" : "+") : "";
  const magnitude = signed ? Math.abs(display) : display;

  return (
    <span className={className}>
      {sign}
      {prefix}
      {magnitude.toFixed(precision)}
      {suffix}
    </span>
  );
}
