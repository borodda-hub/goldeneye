"use client";

import { useEffect, useRef, useState } from "react";

export type FlashDirection = "up" | "down" | null;

/**
 * Briefly flag direction when `price` changes. Returns "up" / "down" for ~400ms
 * after a change, then null. First non-null observation does not flash.
 */
export function usePriceFlash(
  price: number | null | undefined,
  durationMs = 400,
): FlashDirection {
  const prevRef = useRef<number | null>(null);
  const [flash, setFlash] = useState<FlashDirection>(null);

  useEffect(() => {
    if (price == null) return;
    const prev = prevRef.current;
    prevRef.current = price;
    if (prev == null || prev === price) return;
    setFlash(price > prev ? "up" : "down");
    const t = setTimeout(() => setFlash(null), durationMs);
    return () => clearTimeout(t);
  }, [price, durationMs]);

  return flash;
}

/** Tailwind utility classes for a soft flash background. */
export function flashBgClass(flash: FlashDirection): string {
  if (flash === "up") return "bg-up-soft";
  if (flash === "down") return "bg-down-soft";
  return "";
}
