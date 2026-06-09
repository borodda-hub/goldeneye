"use client";

import { PageHeader } from "@/components/PageHeader";
import { SampleDeskBanner } from "@/components/SampleDeskBanner";
import { Skeleton, SkeletonText } from "@/components/Skeleton";
import { BucketTable } from "@/components/calibration/BucketTable";
import { CalibrationSummary } from "@/components/calibration/CalibrationSummary";
import { DQCoachPanel } from "@/components/calibration/DQCoachPanel";
import { DeskCalibrationCard } from "@/components/calibration/DeskCalibrationCard";
import { ModelDiagnosticsCard } from "@/components/calibration/ModelDiagnosticsCard";
import { ReliabilityDiagram } from "@/components/calibration/ReliabilityDiagram";
import type { CalibrationResponse } from "@/lib/api";
import { markStep } from "@/lib/onboarding";
import { useCalibration } from "@/lib/queries";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { Gauge } from "lucide-react";
import { useEffect } from "react";

interface Props {
  initialData: CalibrationResponse | null;
  initialSymbol?: string;
}

export function CalibrationShell({ initialData, initialSymbol = "NG" }: Props) {
  const { activeSymbol } = useActiveInstrument();
  // Visiting Calibration closes the onboarding decision loop.
  useEffect(() => markStep("calibration"), []);
  const { data: fetched, isLoading } = useCalibration(activeSymbol, 5);
  const fromQuery = fetched as CalibrationResponse | undefined;
  const data =
    fromQuery ?? (activeSymbol === initialSymbol ? initialData : null);

  if (isLoading && !data) {
    return (
      <div className="stagger flex flex-col gap-6">
        <PageHeader
          icon={Gauge}
          title="Decision Calibration"
          subtitle="Forecast reliability · diagnostics"
        />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div className="lg:col-span-2 flex flex-col gap-6 min-w-0">
            <div className="border border-line-1 bg-surface-1 p-5">
              <SkeletonText lines={3} />
            </div>
            <Skeleton className="h-[48vh] min-h-[300px] w-full" />
            <div className="border border-line-1 bg-surface-1 p-5">
              <SkeletonText lines={5} />
            </div>
          </div>
          <aside className="lg:col-span-1 min-w-0">
            <div className="border border-line-1 bg-surface-1 p-5">
              <SkeletonText lines={6} />
            </div>
          </aside>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6 py-12 max-w-3xl">
        <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          <span
            aria-hidden="true"
            className="inline-block w-[18px] h-px bg-accent"
          />
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
    <div className="stagger flex flex-col gap-6">
      <PageHeader
        icon={Gauge}
        title="Decision Calibration"
        subtitle="Forecast reliability · diagnostics"
        right={
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent border border-line-1 bg-surface-1 px-2 py-1 rounded-sm">
            {data.instrument_code}
          </span>
        }
      />

      <SampleDeskBanner />

      <header className="flex flex-col gap-3 border-b border-line-1 pb-4">
        <h2 className="font-serif text-[40px] leading-[1.02] tracking-[-0.015em] text-ink-1">
          How well do your{" "}
          <span
            className="italic text-accent-bright"
            style={{ fontVariationSettings: '"opsz" 72, "SOFT" 80' }}
          >
            convictions
          </span>{" "}
          calibrate?
        </h2>
        <p className="text-sm text-ink-3 leading-relaxed max-w-3xl">
          Reliability diagram across your logged journal entries. Perfect
          calibration sits on the diagonal: a 70% conviction band should resolve
          as hits 70% of the time. Bands below the diagonal are over-confident,
          bands above are under-confident.
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

      {/* Model Health: per-model failure diagnostics over the backtest window
          (calibration vs sharpness, directional bias, regime accuracy, drift). */}
      <ModelDiagnosticsCard symbol={data.instrument_code} />

      {/* Desk-wide: per-analyst skill-vs-luck across all decisions. Spans the
          full width because it's cross-instrument, not NG-specific. */}
      <DeskCalibrationCard />
    </div>
  );
}
