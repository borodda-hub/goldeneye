"use client";

import type { CalibrationResponse } from "@/lib/api";
import { useCalibration } from "@/lib/queries";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { CalibrationSummary } from "@/components/calibration/CalibrationSummary";
import { ReliabilityDiagram } from "@/components/calibration/ReliabilityDiagram";
import { BucketTable } from "@/components/calibration/BucketTable";
import { DQCoachPanel } from "@/components/calibration/DQCoachPanel";

interface Props {
  initialData: CalibrationResponse | null;
  initialSymbol?: string;
}

export function CalibrationShell({
  initialData,
  initialSymbol = "NG",
}: Props) {
  const { activeSymbol } = useActiveInstrument();
  const { data: fetched, isLoading } = useCalibration(activeSymbol, 5);
  const fromQuery = fetched as CalibrationResponse | undefined;
  const data =
    fromQuery ?? (activeSymbol === initialSymbol ? initialData : null);

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center py-24 text-ink-3 font-mono">
        Loading calibration…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6 py-12 max-w-3xl">
        <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          <span aria-hidden="true" className="inline-block w-[18px] h-px bg-accent" />
          Decision Calibration
        </span>
        <p className="text-sm text-ink-3">
          Calibration data unavailable. Make sure the API is up and a journal
          entry has been logged.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3 border-b border-line-1 pb-4">
        <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          <span aria-hidden="true" className="inline-block w-[18px] h-px bg-accent" />
          Decision Calibration · {data.instrument_code}
        </span>
        <h1 className="font-serif text-[40px] leading-[1.02] tracking-[-0.015em] text-ink-1">
          How well do your{" "}
          <span
            className="italic text-accent-bright"
            style={{ fontVariationSettings: '"opsz" 72, "SOFT" 80' }}
          >
            convictions
          </span>{" "}
          calibrate?
        </h1>
        <p className="text-sm text-ink-3 leading-relaxed max-w-3xl">
          Reliability diagram across your logged journal entries. Perfect
          calibration sits on the diagonal: a 70% conviction band should
          resolve as hits 70% of the time. Bands below the diagonal are
          over-confident, bands above are under-confident.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left column: the existing data view (summary + diagram + table) */}
        <div className="lg:col-span-2 flex flex-col gap-6 min-w-0">
          <CalibrationSummary data={data} />
          <ReliabilityDiagram buckets={data.buckets} />
          <BucketTable buckets={data.buckets} />
        </div>

        {/* Right column: LLM-synthesized DQ coaching */}
        <aside className="lg:col-span-1 min-w-0">
          <DQCoachPanel instrumentCode={data.instrument_code} />
        </aside>
      </div>
    </div>
  );
}
