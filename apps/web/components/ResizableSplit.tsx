"use client";

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
  /** className applied to the outer flex container (e.g. height, gap). */
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

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      draggingRef.current = true;
      (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [],
  );

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

  return (
    <div
      ref={containerRef}
      className={`flex ${className}`}
      data-testid="resizable-split"
    >
      <div className="flex-1 min-w-0">{left}</div>
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
      <div className="shrink-0" style={{ width: `${rightWidth}px` }}>
        {right}
      </div>
    </div>
  );
}
