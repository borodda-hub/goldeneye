"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { CalibrationBucket } from "@/lib/api";
import { colors } from "@/lib/colors";

interface Props {
  buckets: CalibrationBucket[];
}

interface ChartPoint {
  claimed: number;
  actual: number;
  total: number;
  label: string;
}

function bucketsToPoints(buckets: CalibrationBucket[]): ChartPoint[] {
  return buckets
    .filter(
      (b) => b.hit_rate !== null && b.claimed_mean !== null && b.total_count > 0,
    )
    .map((b) => ({
      claimed: Number(b.claimed_mean),
      actual: (b.hit_rate ?? 0) * 100,
      total: b.total_count,
      label: b.label,
    }));
}

const DIAGONAL: { x: number; y: number }[] = [
  { x: 0, y: 0 },
  { x: 100, y: 100 },
];

function PointTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: ChartPoint }> }) {
  if (!active || !payload || payload.length === 0 || !payload[0].payload) return null;
  const p = payload[0].payload;
  return (
    <div className="border border-line-2 bg-surface-1 px-3 py-2 text-xs font-mono">
      <div className="text-ink-3">Bucket {p.label}</div>
      <div className="text-ink-1">
        Claimed: <span className="text-accent-bright">{p.claimed.toFixed(0)}%</span>
      </div>
      <div className="text-ink-1">
        Actual: <span className="text-accent-bright">{p.actual.toFixed(0)}%</span>
      </div>
      <div className="text-ink-3 mt-1">n={p.total}</div>
    </div>
  );
}

export function ReliabilityDiagram({ buckets }: Props) {
  const points = bucketsToPoints(buckets);
  const hasPoints = points.length > 0;

  return (
    <section
      aria-label="Reliability diagram"
      data-tour="reliability-diagram"
      className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-3"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          Reliability diagram
        </span>
        {hasPoints ? (
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-4">
            {points.length} buckets · diagonal = perfect calibration
          </span>
        ) : null}
      </div>

      <div className="h-[48vh] min-h-[300px]">
        {!hasPoints ? (
          <div className="h-full flex items-center justify-center text-sm text-ink-4 font-mono">
            No buckets have ≥ 3 resolved entries yet. Log + resolve more
            journal entries to populate the diagram.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 16, right: 16, bottom: 32, left: 32 }}>
              <CartesianGrid stroke={colors.line1} strokeDasharray="2 2" />
              <XAxis
                type="number"
                dataKey="claimed"
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                tick={{ fontSize: 10, fill: colors.ink3 }}
                axisLine={{ stroke: colors.line1 }}
                tickLine={false}
                label={{
                  value: "Claimed conviction (%)",
                  position: "insideBottom",
                  offset: -16,
                  style: {
                    fontSize: 10,
                    fill: colors.ink3,
                    letterSpacing: "0.22em",
                    textTransform: "uppercase",
                  },
                }}
              />
              <YAxis
                type="number"
                dataKey="actual"
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                tick={{ fontSize: 10, fill: colors.ink3 }}
                axisLine={{ stroke: colors.line1 }}
                tickLine={false}
                label={{
                  value: "Actual hit rate (%)",
                  angle: -90,
                  position: "insideLeft",
                  offset: -8,
                  style: {
                    fontSize: 10,
                    fill: colors.ink3,
                    letterSpacing: "0.22em",
                    textTransform: "uppercase",
                  },
                }}
              />
              <ZAxis
                type="number"
                dataKey="total"
                range={[40, 240]}
                name="Sample size"
              />
              <ReferenceLine
                segment={[
                  { x: 0, y: 0 },
                  { x: 100, y: 100 },
                ]}
                stroke={colors.accentDeep}
                strokeDasharray="4 4"
                ifOverflow="extendDomain"
              />
              <Tooltip content={<PointTooltip />} cursor={{ stroke: colors.line2 }} />
              <Scatter
                name="Observed"
                data={points}
                fill={colors.accentBright}
                stroke={colors.accent}
                strokeWidth={1.5}
              />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
