"use client";

import { PageHeader } from "@/components/PageHeader";
import { SampleDeskBanner } from "@/components/SampleDeskBanner";
import { Skeleton, SkeletonText } from "@/components/Skeleton";
import { GoldItalic } from "@/components/typography";
import { LiveProofStrip } from "@/components/validation/LiveProofStrip";
import { MethodStrip } from "@/components/validation/MethodStrip";
import { ValidationLedgerTable } from "@/components/validation/ValidationLedgerTable";
import type { ValidationResponse } from "@/lib/api";
import { useValidation } from "@/lib/queries";
import { Microscope } from "lucide-react";

interface Props {
  initialData: ValidationResponse | null;
}

const RERUN_COMMANDS = [
  "python -m seeds.validate_engine_oos --alt-only",
  "python -m seeds.validate_vol_real",
  "python -m seeds.validate_d1_vol_premium",
  "python -m seeds.validate_d2_carry",
  "python -m seeds.validate_d4_storage_event",
];

export function ValidationShell({ initialData }: Props) {
  const { data: fetched, isLoading } = useValidation();
  const data = fetched ?? initialData;

  if (!data && isLoading) {
    return (
      <div className="stagger flex flex-col gap-6">
        <PageHeader
          icon={Microscope}
          title="How We Validate"
          subtitle="model diligence · provenance ledger"
        />
        <Skeleton className="h-24 w-full max-w-3xl" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <SkeletonText lines={8} />
      </div>
    );
  }

  return (
    <div className="stagger flex flex-col gap-6" data-tour="validation-shell">
      <PageHeader
        icon={Microscope}
        title="How We Validate"
        subtitle="model diligence · provenance ledger"
      />

      <header className="flex flex-col gap-3 border-b border-line-1 pb-4">
        <h2 className="font-serif text-[40px] leading-[1.02] tracking-[-0.015em] text-ink-1">
          We publish what our models <GoldItalic>can’t</GoldItalic> do.
        </h2>
        <p className="max-w-3xl text-sm leading-relaxed text-ink-3">
          One claim has survived real out-of-sample testing: the price-range
          bands are calibrated. Directional prediction has been tested the same
          way and has not earned a claim — so the terminal frames direction as
          views, never probabilities. Everything below is a tested verdict with
          its data provenance, reproducible from the repository in one command.
        </p>
      </header>

      <MethodStrip />

      {data ? <ValidationLedgerTable rows={data.rows} /> : null}

      <SampleDeskBanner />
      <LiveProofStrip data={data ?? null} />

      <div className="rounded-md border border-line-1 bg-surface-1 px-4 py-3">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Reproduce it
        </span>
        <p className="mt-1.5 font-mono text-[9px] leading-relaxed text-ink-4">
          Each verdict re-runs from the repository (
          <span className="text-ink-3">uv run --directory apps/api …</span>):
        </p>
        <ul className="mt-1 flex flex-col gap-0.5">
          {RERUN_COMMANDS.map((c) => (
            <li key={c} className="font-mono text-[9px] text-ink-3">
              {c}
            </li>
          ))}
        </ul>
        <p className="mt-2 border-t border-line-1 pt-2 font-mono text-[9px] leading-relaxed text-ink-4">
          Gates live in <span className="text-ink-3">docs/PHASE_*_PLAN.md</span>
          , committed before each run · the claims ledger is{" "}
          <span className="text-ink-3">docs/MODEL_DILIGENCE.md</span> ·
          walk-forward safety is enforced by CI, including a cheating-model
          proof.
        </p>
      </div>
    </div>
  );
}
