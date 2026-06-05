"use client";

import { useReducedMotion } from "@/lib/useReducedMotion";

interface Props {
  /** Unique gradient id; reference it as fill={`url(#${id})`}. */
  id: string;
  /** Accent color of the sweeping band — pass the chart's own line color. */
  color: string;
  /** Seconds per sweep. Stagger across charts so they drift out of phase. */
  durationSec?: number;
  /** Peak opacity at the band's center. Keep it subtle. */
  peakOpacity?: number;
}

/**
 * A `<linearGradient>` whose soft bright band translates across the bounding
 * box, producing a slow sheen that sweeps over an area-chart fill. Drop it
 * inside a `<defs>` and fill an overlay `<Area>` with `url(#id)`.
 *
 * The band is transparent at both extremes of its travel, so the loop restart
 * is invisible. Honors `prefers-reduced-motion`: the band collapses to fully
 * transparent (the chart just shows its normal fill, no static stripe).
 */
export function SheenGradient({
  id,
  color,
  durationSec = 7,
  peakOpacity = 0.3,
}: Props) {
  const reduce = useReducedMotion();
  const peak = reduce ? 0 : peakOpacity;
  return (
    <linearGradient
      id={id}
      x1="0"
      y1="0"
      x2="1"
      y2="0.35"
      gradientUnits="objectBoundingBox"
    >
      <stop offset="0" stopColor={color} stopOpacity={0} />
      <stop offset="0.25" stopColor={color} stopOpacity={peak * 0.15} />
      <stop offset="0.5" stopColor={color} stopOpacity={peak} />
      <stop offset="0.75" stopColor={color} stopOpacity={peak * 0.15} />
      <stop offset="1" stopColor={color} stopOpacity={0} />
      {!reduce && (
        <animateTransform
          attributeName="gradientTransform"
          type="translate"
          from="-0.9 0"
          to="0.9 0"
          dur={`${durationSec}s`}
          repeatCount="indefinite"
        />
      )}
    </linearGradient>
  );
}
