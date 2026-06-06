import { NumberCell } from "@/components/NumberCell";
import type { CalibrationResponse } from "@/lib/api";
import { Newspaper, Sigma } from "lucide-react";

interface Props {
  data: CalibrationResponse;
}

export function CalibrationSummary({ data }: Props) {
  return (
    <section
      aria-label="Calibration summary"
      className="card-interactive grid grid-cols-3 gap-6 border border-line-1 bg-surface-1 p-5"
    >
      <div className="col-span-2 flex flex-col gap-3 border-r border-line-1 pr-6">
        <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          <Newspaper
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Headline
        </span>
        {data.summary ? (
          <p className="font-serif text-[24px] leading-snug text-ink-1 tracking-[-0.01em]">
            {data.summary.split(" resolved at ").map((chunk, i, arr) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
              <span key={i}>
                {chunk}
                {i < arr.length - 1 ? (
                  <span
                    className="italic text-accent-bright"
                    style={{ fontVariationSettings: '"opsz" 72, "SOFT" 80' }}
                  >
                    {" resolved at "}
                  </span>
                ) : null}
              </span>
            ))}
          </p>
        ) : (
          <p className="text-sm text-ink-3 leading-relaxed">
            All conviction buckets calibrate within 5 percentage points of their
            claimed level. Either your decision quality is on-pace or the sample
            size is still too small to detect drift.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          <Sigma
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Sample
        </span>
        <div className="flex flex-col gap-1.5">
          <SampleRow label="Total entries" value={data.total_entries} />
          <SampleRow label="Resolved" value={data.resolved_entries} />
          <SampleRow label="Unresolved" value={data.unresolved_entries} />
        </div>
      </div>
    </section>
  );
}

function SampleRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
        {label}
      </span>
      <span className="font-mono tabular-nums text-sm text-ink-1">{value}</span>
    </div>
  );
}
