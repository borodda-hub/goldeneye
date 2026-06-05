"use client";

import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
  SeriesAttachedParameter,
  SeriesType,
  Time,
  UTCTimestamp,
} from "lightweight-charts";
import {
  type Drawing,
  type DrawingPoint,
  FIB_LEVELS,
  type Pt,
  distanceToHline,
  distanceToRectBorder,
  distanceToSegment,
} from "./drawings";

const HANDLE_R = 4;
const HIT_TOLERANCE = 6;

// Minimal structural view of fancy-canvas's render target/scope — we only use
// useMediaCoordinateSpace + the CSS-pixel context + media width. The real
// CanvasRenderingTarget2D is structurally assignable to this.
interface MediaScope {
  context: CanvasRenderingContext2D;
  mediaSize: { width: number; height: number };
}
interface RenderTarget {
  useMediaCoordinateSpace(callback: (scope: MediaScope) => void): void;
}

/**
 * Renders one {@link Drawing} on the price pane and hit-tests it for selection.
 * Anchors are stored in {time, price}; pixels are computed at draw time via the
 * series/timeScale coordinate functions, so drawings stay glued to the data.
 */
export class DrawingPrimitive implements ISeriesPrimitive<Time> {
  drawing: Drawing;
  selected: boolean;
  private chart: IChartApi | null = null;
  private series: ISeriesApi<SeriesType> | null = null;
  private req: (() => void) | null = null;

  constructor(drawing: Drawing, selected: boolean) {
    this.drawing = drawing;
    this.selected = selected;
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this.chart = param.chart as IChartApi;
    this.series = param.series as ISeriesApi<SeriesType>;
    this.req = param.requestUpdate;
  }

  detached(): void {
    this.chart = null;
    this.series = null;
    this.req = null;
  }

  /** Force a redraw after mutating `drawing`/`selected` (used by the preview). */
  requestRedraw(): void {
    try {
      this.req?.();
    } catch {
      // chart disposed mid-interaction — ignore.
    }
  }

  updateAllViews(): void {}

  paneViews(): readonly IPrimitivePaneView[] {
    return [
      {
        zOrder: (): PrimitivePaneViewZOrder => "top",
        renderer: (): IPrimitivePaneRenderer => ({
          draw: (target: RenderTarget) => this.render(target),
        }),
      },
    ];
  }

  hitTest(x: number, y: number): PrimitiveHoveredItem | null {
    const d = this.distance(x, y);
    if (d === null || d > HIT_TOLERANCE) return null;
    return {
      distance: d,
      externalId: this.drawing.id,
      zOrder: "top",
      cursorStyle: "move",
    };
  }

  // ── coordinate + geometry ──────────────────────────────────────────────
  private px(pt: DrawingPoint): Pt | null {
    if (!this.chart || !this.series) return null;
    const x = this.chart.timeScale().timeToCoordinate(pt.time as UTCTimestamp);
    const y = this.series.priceToCoordinate(pt.price);
    if (x === null || y === null) return null;
    return { x, y };
  }

  private paneWidth(): number {
    try {
      return this.chart?.timeScale().width() ?? 4000;
    } catch {
      return 4000;
    }
  }

  /** Extend the a→b direction to the pane edge (for rays). */
  private extend(a: Pt, b: Pt, w: number): Pt {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    if (Math.abs(dx) < 1e-6) return { x: b.x, y: dy >= 0 ? 1e5 : -1e5 };
    const targetX = dx > 0 ? w : 0;
    const t = (targetX - a.x) / dx;
    return { x: a.x + dx * t, y: a.y + dy * t };
  }

  private distance(x: number, y: number): number | null {
    const raw = this.drawing.points.map((p) => this.px(p));
    if (raw.some((p) => p === null)) return null;
    const p = raw as Pt[];
    const c: Pt = { x, y };
    switch (this.drawing.type) {
      case "hline":
        return distanceToHline(c, p[0].y);
      case "trendline":
        return distanceToSegment(c, p[0], p[1]);
      case "ray":
        return distanceToSegment(
          c,
          p[0],
          this.extend(p[0], p[1], this.paneWidth()),
        );
      case "rectangle":
        return distanceToRectBorder(c, p[0], p[1]);
      case "fib": {
        // Nearest of the horizontal fib levels between the two anchors.
        const lo = Math.min(p[0].y, p[1].y);
        const hi = Math.max(p[0].y, p[1].y);
        return Math.min(
          ...FIB_LEVELS.map((lvl) => Math.abs(c.y - (lo + (hi - lo) * lvl))),
        );
      }
      case "text":
        return Math.hypot(c.x - p[0].x, c.y - p[0].y);
      default:
        return null;
    }
  }

  // ── rendering ──────────────────────────────────────────────────────────
  private render(target: RenderTarget): void {
    target.useMediaCoordinateSpace((scope) => {
      const ctx = scope.context;
      const w = scope.mediaSize.width;
      const raw = this.drawing.points.map((p) => this.px(p));
      if (raw.some((p) => p === null)) return;
      const p = raw as Pt[];

      ctx.save();
      ctx.strokeStyle = this.drawing.color;
      ctx.fillStyle = this.drawing.color;
      ctx.lineWidth = this.drawing.width;
      ctx.lineJoin = "round";
      ctx.font = "11px 'JetBrains Mono', monospace";

      switch (this.drawing.type) {
        case "hline":
          line(ctx, 0, p[0].y, w, p[0].y);
          break;
        case "trendline":
          line(ctx, p[0].x, p[0].y, p[1].x, p[1].y);
          break;
        case "ray": {
          const e = this.extend(p[0], p[1], w);
          line(ctx, p[0].x, p[0].y, e.x, e.y);
          break;
        }
        case "rectangle": {
          const x = Math.min(p[0].x, p[1].x);
          const y = Math.min(p[0].y, p[1].y);
          const rw = Math.abs(p[1].x - p[0].x);
          const rh = Math.abs(p[1].y - p[0].y);
          ctx.globalAlpha = 0.08;
          ctx.fillRect(x, y, rw, rh);
          ctx.globalAlpha = 1;
          ctx.strokeRect(x, y, rw, rh);
          break;
        }
        case "fib": {
          const x1 = Math.min(p[0].x, p[1].x);
          const x2 = Math.max(p[0].x, p[1].x);
          const top = this.drawing.points[0].price;
          const bot = this.drawing.points[1].price;
          for (const lvl of FIB_LEVELS) {
            const yc = this.series?.priceToCoordinate(top + (bot - top) * lvl);
            if (yc === null || yc === undefined) continue;
            ctx.globalAlpha = 0.7;
            line(ctx, x1, yc, x2, yc);
            ctx.globalAlpha = 1;
            const price = (top + (bot - top) * lvl).toFixed(3);
            ctx.fillText(
              `${(lvl * 100).toFixed(1)}%  ${price}`,
              x2 + 4,
              yc - 2,
            );
          }
          break;
        }
        case "text":
          ctx.font = "12px 'JetBrains Mono', monospace";
          ctx.fillText(this.drawing.text ?? "", p[0].x, p[0].y);
          break;
      }

      if (this.selected) {
        for (const pt of p) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, HANDLE_R, 0, Math.PI * 2);
          ctx.fillStyle = this.drawing.color;
          ctx.fill();
          ctx.lineWidth = 1;
          ctx.strokeStyle = "#000";
          ctx.stroke();
        }
      }
      ctx.restore();
    });
  }
}

function line(
  ctx: CanvasRenderingContext2D,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): void {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}
