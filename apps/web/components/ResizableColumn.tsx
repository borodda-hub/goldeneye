"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Side = "left" | "right";

interface Props {
  /** Which edge holds the drag handle. "right" = handle on the right edge
   * (use for a left-rail column like the watchlist). "left" = handle on the
   * left edge (use for a right-rail column like the equity/positions rail). */
  side: Side;
  defaultWidth: number;
  minWidth?: number;
  maxWidth?: number;
  /** Optional localStorage key — persist the width across reloads. */
  storageKey?: string;
  /** Applied to the outer container (e.g. for sticky positioning, height). */
  className?: string;
  children: React.ReactNode;
}

const HANDLE_WIDTH_PX = 6;

/**
 * A fixed-width column with a draggable handle on one edge. Sibling to
 * ResizableSplit but for when you want to inject a resizable rail into an
 * existing flex layout without restructuring it as a 2-pane split.
 *
 * Pair two of these (side="right" on the left rail, side="left" on the
 * right rail) around a flex-1 main column to get a 3-column resizable
 * dashboard.
 */
export function ResizableColumn({
  side,
  defaultWidth,
  minWidth = 180,
  maxWidth = 560,
  storageKey,
  className = "",
  children,
}: Props) {
  const [width, setWidth] = useState<number>(defaultWidth);
  const draggingRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const n = Number(raw);
        if (Number.isFinite(n) && n > 0) setWidth(n);
      }
    } catch {
      // ignore
    }
  }, [storageKey]);

  const clamp = useCallback(
    (n: number) => {
      if (n < minWidth) return minWidth;
      if (n > maxWidth) return maxWidth;
      return n;
    },
    [minWidth, maxWidth],
  );

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    draggingRef.current = true;
    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) return;
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const next =
        side === "right" ? e.clientX - rect.left : rect.right - e.clientX;
      setWidth(clamp(next));
    },
    [clamp, side],
  );

  const onPointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      (e.currentTarget as HTMLDivElement).releasePointerCapture(e.pointerId);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      if (storageKey) {
        try {
          localStorage.setItem(storageKey, String(Math.round(width)));
        } catch {
          // ignore
        }
      }
    },
    [storageKey, width],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const STEP = 16;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setWidth((w) => clamp(side === "right" ? w - STEP : w + STEP));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setWidth((w) => clamp(side === "right" ? w + STEP : w - STEP));
      }
    },
    [clamp, side],
  );

  const handle = (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize column"
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
      className="group relative shrink-0 flex items-center justify-center cursor-col-resize focus:outline-none"
      style={{ width: `${HANDLE_WIDTH_PX}px` }}
      data-testid="resizable-column-handle"
    >
      <span
        aria-hidden="true"
        className="h-full w-px bg-line-1 group-hover:bg-accent group-focus:bg-accent transition-colors"
      />
    </div>
  );

  return (
    <div
      ref={containerRef}
      className={`flex ${className}`}
      data-testid="resizable-column"
    >
      {side === "left" && handle}
      <div
        className="min-w-0 flex-1"
        style={{ width: `${width}px`, flex: `0 0 ${width}px` }}
      >
        {children}
      </div>
      {side === "right" && handle}
    </div>
  );
}
