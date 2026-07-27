"use client";

import { useMediaQuery } from "@/lib/useMediaQuery";
import { useCallback, useEffect, useRef, useState } from "react";

interface Props {
  left: React.ReactNode;
  right: React.ReactNode;
  /** Initial width (px) of the right pane on first load. */
  defaultRightWidth?: number;
  /** Don't allow the right pane to shrink below this many pixels. */
  rightMinWidth?: number;
  /** Don't allow the left pane (computed) to shrink below this many pixels. */
  leftMinWidth?: number;
  /** Optional localStorage key — persist the user's width across reloads. */
  storageKey?: string;
  /**
   * className applied to the split's height/layout. In the wide (≥`lg`) two-pane
   * layout it's the container height; when stacked (< `lg`) it's applied to EACH
   * pane so charts keep an explicit height and cards size exactly as they do on
   * desktop — just stacked vertically. Keep it to height/min-height utilities.
   */
  className?: string;
}

const HANDLE_WIDTH_PX = 6;

/**
 * Two-pane horizontal split with a draggable handle. The left pane is
 * fluid (flex-1) and absorbs all the space the right pane doesn't claim.
 * Drag the handle to resize.
 */
export function ResizableSplit({
  left,
  right,
  defaultRightWidth = 288,
  rightMinWidth = 220,
  leftMinWidth = 280,
  storageKey,
  className = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rightWidth, setRightWidth] = useState<number>(defaultRightWidth);
  const draggingRef = useRef(false);
  // Below `lg` (tablet/phone) the fixed-px two-pane split + drag handle can't fit
  // and overlaps; stack vertically instead. Defaults to wide on SSR/first paint
  // so desktop markup is stable (no hydration mismatch), then syncs after mount.
  const isWide = useMediaQuery("(min-width: 1024px)", true);
  // Phase U1: the split must be CONTAINER-aware, not just viewport-aware — a
  // wide viewport with rails can still hand this component a container
  // narrower than leftMin+rightMin (the 2px-wide-card bug). Measure the
  // available width and (a) stack when two panes can't honestly fit,
  // (b) clamp the persisted px width to what the container affords at
  // RENDER time, not only during drag.
  const [containerW, setContainerW] = useState<number | null>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (typeof w === "number") setContainerW(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  });
  const fitsSideBySide =
    containerW === null
      ? isWide
      : containerW >= leftMinWidth + rightMinWidth + HANDLE_WIDTH_PX;
  const effectiveRight =
    containerW === null
      ? rightWidth
      : Math.max(
          rightMinWidth,
          Math.min(rightWidth, containerW - leftMinWidth - HANDLE_WIDTH_PX),
        );

  // Hydrate from localStorage after mount to avoid SSR mismatch.
  useEffect(() => {
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const n = Number(raw);
        if (Number.isFinite(n) && n > 0) setRightWidth(n);
      }
    } catch {
      // ignore
    }
  }, [storageKey]);

  const clampWidth = useCallback(
    (next: number) => {
      const container = containerRef.current;
      const containerWidth = container?.getBoundingClientRect().width ?? 0;
      const maxRight = Math.max(
        rightMinWidth,
        containerWidth - leftMinWidth - HANDLE_WIDTH_PX,
      );
      if (next < rightMinWidth) return rightMinWidth;
      if (next > maxRight) return maxRight;
      return next;
    },
    [leftMinWidth, rightMinWidth],
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
      // Right-pane width = distance from pointer to the container's right edge.
      const next = clampWidth(rect.right - e.clientX);
      setRightWidth(next);
    },
    [clampWidth],
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
          localStorage.setItem(storageKey, String(Math.round(rightWidth)));
        } catch {
          // ignore
        }
      }
    },
    [rightWidth, storageKey],
  );

  // Keyboard nudges: arrow-left / arrow-right while focused steps 16 px.
  const onHandleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setRightWidth((w) => clampWidth(w + 16));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setRightWidth((w) => clampWidth(w - 16));
      }
    },
    [clampWidth],
  );

  // Stacked layout (< lg): full-width panes in a vertical column, no drag handle,
  // no persisted px width. Each pane keeps the row's height so charts render and
  // cards size exactly as on desktop — they just stack instead of sitting side by
  // side. This is what makes the dashboard reflow like every other page on
  // tablet/mobile instead of overlapping.
  if (!isWide || !fitsSideBySide) {
    return (
      <div
        ref={containerRef}
        className="flex flex-col gap-4"
        data-testid="resizable-split"
      >
        <div className={`w-full min-w-0 ${className}`}>{left}</div>
        <div className={`w-full min-w-0 ${className}`}>{right}</div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex ${className}`}
      data-testid="resizable-split"
    >
      <div className="flex-1 min-w-0">{left}</div>
      {/* biome-ignore lint/a11y/useSemanticElements: interactive drag handle using role="separator"; native <hr> cannot host pointer/keyboard handlers or child affordance */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize columns"
        tabIndex={0}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={onHandleKeyDown}
        className="group relative shrink-0 flex items-center justify-center cursor-col-resize focus:outline-none"
        style={{ width: `${HANDLE_WIDTH_PX}px` }}
        data-testid="resizable-split-handle"
      >
        {/* Visible 1px line, expands to 2px on hover/focus for affordance. */}
        <span
          aria-hidden="true"
          className="h-full w-px bg-line-1 group-hover:bg-accent group-focus:bg-accent transition-colors"
        />
      </div>
      <div className="shrink-0" style={{ width: `${effectiveRight}px` }}>
        {right}
      </div>
    </div>
  );
}
