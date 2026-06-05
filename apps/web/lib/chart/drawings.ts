"use client";

/**
 * Manual chart drawings. A drawing stores its anchor points in chart data space
 * (`{time, price}`) — never pixels — so it re-renders correctly across zoom,
 * pan, and timeframe switches. Persisted per-symbol (a daily trendline shows on
 * the weekly chart too). Rendering lives in DrawingPrimitive; placement/selection
 * interaction lives in PriceChart.
 */

export type DrawingType =
  | "hline"
  | "trendline"
  | "ray"
  | "rectangle"
  | "fib"
  | "text";

/** Toolbar tool: the cursor (select/pan), a drawing type, or the measure tool. */
export type DrawingTool = "cursor" | DrawingType | "measure";

export interface DrawingPoint {
  /** UTCTimestamp (epoch seconds). */
  time: number;
  price: number;
}

export interface Drawing {
  id: string;
  type: DrawingType;
  points: DrawingPoint[];
  color: string;
  width: number;
  /** Label text (text drawings only). */
  text?: string;
}

/** Clicks required to finalize each drawing type. */
export const POINTS_NEEDED: Record<DrawingType, number> = {
  hline: 1,
  trendline: 2,
  ray: 2,
  rectangle: 2,
  fib: 2,
  text: 1,
};

export const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

const STORAGE_PREFIX = "goldeneye:chart:drawings:";

export function loadDrawings(symbol: string): Drawing[] {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + symbol);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Drawing[]) : [];
  } catch {
    return [];
  }
}

export function saveDrawings(symbol: string, drawings: Drawing[]): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + symbol, JSON.stringify(drawings));
  } catch {
    // localStorage unavailable (incognito / quota) — ignore.
  }
}

export function newDrawingId(): string {
  return `d_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

// ── Pure geometry (pixel space) — unit-tested, used for hit-testing ──────────

export interface Pt {
  x: number;
  y: number;
}

/** Shortest distance from point `p` to the segment `a`–`b`. */
export function distanceToSegment(p: Pt, a: Pt, b: Pt): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

/** Vertical distance from `p` to a full-width horizontal line at `y`. */
export function distanceToHline(p: Pt, y: number): number {
  return Math.abs(p.y - y);
}

/** Shortest distance from `p` to the border of the rect spanned by `a`,`b`. */
export function distanceToRectBorder(p: Pt, a: Pt, b: Pt): number {
  const x1 = Math.min(a.x, b.x);
  const x2 = Math.max(a.x, b.x);
  const y1 = Math.min(a.y, b.y);
  const y2 = Math.max(a.y, b.y);
  const tl = { x: x1, y: y1 };
  const tr = { x: x2, y: y1 };
  const br = { x: x2, y: y2 };
  const bl = { x: x1, y: y2 };
  return Math.min(
    distanceToSegment(p, tl, tr),
    distanceToSegment(p, tr, br),
    distanceToSegment(p, br, bl),
    distanceToSegment(p, bl, tl),
  );
}
