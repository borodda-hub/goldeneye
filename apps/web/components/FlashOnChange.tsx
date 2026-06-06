"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  /** The numeric key whose change drives the flash (direction from its sign). */
  value: number | null | undefined;
  className?: string;
  /** Pre-formatted content to display (e.g. "+$1,240", "3.512"). */
  children: React.ReactNode;
}

/**
 * Wraps arbitrary pre-formatted content and tints it green/red for ~0.65s
 * whenever `value` ticks up/down — the classic terminal "live number" cue.
 * Pure CSS (`.flash-up` / `.flash-down`), so it honors prefers-reduced-motion.
 * Use NumberCell for plain numbers; use this for formatted/currency strings.
 */
export function FlashOnChange({ value, className = "", children }: Props) {
  const prev = useRef(value);
  const [flashCls, setFlashCls] = useState("");
  useEffect(() => {
    const p = prev.current;
    if (typeof value === "number" && typeof p === "number" && value !== p) {
      setFlashCls(value > p ? "flash-up" : "flash-down");
      const id = setTimeout(() => setFlashCls(""), 650);
      prev.current = value;
      return () => clearTimeout(id);
    }
    prev.current = value;
  }, [value]);
  return <span className={`${className} ${flashCls}`.trim()}>{children}</span>;
}
