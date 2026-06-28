"use client";

import { HelpTip } from "@/components/HelpTip";
import { PageHeader } from "@/components/PageHeader";
import { ResultPanel } from "@/components/scenarios/ResultPanel";
import { RunButton } from "@/components/scenarios/RunButton";
import { ScenarioHistoryList } from "@/components/scenarios/ScenarioHistoryList";
import { ScenarioPreview } from "@/components/scenarios/ScenarioPreview";
import { ShockBuilder } from "@/components/scenarios/ShockBuilder";
import { TemplateGallery } from "@/components/scenarios/TemplateGallery";
import { runScenario } from "@/lib/api";
import { markStep } from "@/lib/onboarding";
import { hasScenarioGeography } from "@/lib/scenarioGeo";
import { useMutation } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";

// WebGL globe — client-only (touches window + three.js).
const ScenarioGlobe = dynamic(
  () =>
    import("@/components/scenarios/ScenarioGlobe").then((m) => m.ScenarioGlobe),
  {
    ssr: false,
    loading: () => (
      <div className="border border-line-1 bg-surface-1 h-[440px] flex items-center justify-center font-mono text-[10px] text-ink-4">
        Loading globe…
      </div>
    ),
  },
);
import type {
  RecentRun,
  ScenarioRunResponse,
  ScenarioTemplate,
  Shock,
} from "./types";

interface Props {
  initialTemplates: ScenarioTemplate[];
  initialRuns: RecentRun[];
}

const INSTRUMENTS: { id: string; label: string }[] = [
  { id: "NG", label: "Natural Gas" },
  { id: "BZ", label: "Brent Crude" },
  // B5: the cross-asset classes are selectable so the Scenario Lab can show its
  // honest "no taxonomy for this asset class yet" state (empty globe + shock
  // builder), instead of hiding them or rendering NG geography for them.
  { id: "ES", label: "S&P 500" },
  { id: "ZN", label: "10Y Treasury" },
];

export function ScenariosShell({ initialTemplates, initialRuns }: Props) {
  const [instrument, setInstrument] = useState<string>("NG");
  const [selected, setSelected] = useState<ScenarioTemplate | null>(null);
  const [shocks, setShocks] = useState<Shock[]>([]);
  const [name, setName] = useState<string>("");
  const [lastResponse, setLastResponse] = useState<ScenarioRunResponse | null>(
    null,
  );

  const mutation = useMutation<ScenarioRunResponse, Error, void>({
    mutationFn: async () => {
      return (await runScenario({
        instrument,
        name: name.trim() || "Untitled scenario",
        shocks: shocks as unknown as Array<Record<string, unknown>>,
      })) as ScenarioRunResponse;
    },
    onSuccess: (data) => {
      setLastResponse(data);
      markStep("scenario");
    },
  });

  // The shock taxonomy is instrument-specific, so switching markets resets the
  // workspace (a gas shock has no meaning on a crude scenario, and vice versa).
  const switchInstrument = (id: string) => {
    if (id === instrument) return;
    setInstrument(id);
    setSelected(null);
    setShocks([]);
    setName("");
    setLastResponse(null);
  };

  const visibleTemplates = initialTemplates.filter(
    (t) => t.instrument === instrument,
  );

  const loadTemplate = (t: ScenarioTemplate) => {
    setSelected(t);
    setShocks(t.shocks);
    setName(t.name);
    setLastResponse(null);
  };

  const canRun = shocks.length > 0 && !mutation.isPending;

  return (
    <div className="stagger flex flex-col gap-4" data-tour="scenario-shell">
      <PageHeader
        icon={FlaskConical}
        title="Scenario Lab"
        subtitle="Stress tests · what-if shocks"
        right={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest">
              {INSTRUMENTS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => switchInstrument(m.id)}
                  aria-pressed={instrument === m.id}
                  className={`px-2 py-1 border transition-colors ${
                    instrument === m.id
                      ? "border-accent text-accent"
                      : "border-line-1 text-ink-4 hover:text-accent"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <HelpTip k="scenarioLab" />
          </div>
        }
      />

      {/* B5: honest unsupported state for asset classes without a scenario taxonomy
          (ES/ZN). The forecast/vol-range/journal surfaces work for them; only the
          Scenario Lab is energy-specific. */}
      {!hasScenarioGeography(instrument) && (
        <div
          className="border border-line-1 bg-surface-1 px-4 py-3 text-[12px] leading-relaxed text-ink-3"
          data-testid="scenario-unsupported"
        >
          <span className="font-medium text-ink-1">
            Scenario Lab isn’t available for {instrument} yet.
          </span>{" "}
          Scenario shocks and the impact globe are modeled for natural gas and
          crude only — this asset class has no scenario taxonomy. Its forecast,
          expected range, and decision-journal surfaces work normally.
        </div>
      )}

      {/* Templates */}
      <section className="flex flex-col gap-2">
        <h2 className="font-mono text-[10px] text-accent uppercase tracking-widest">
          Templates
          <HelpTip k="templates" className="ml-1" />
        </h2>
        <TemplateGallery
          templates={visibleTemplates}
          onSelect={loadTemplate}
          selectedId={selected?.id}
        />
      </section>

      {/* Build → impact: the workspace + recent runs (left) sit next to the
          impact globe (right), with the live preview / narrated result stacked
          beneath the globe — so the page never reads empty. */}
      <section className="grid grid-cols-1 xl:grid-cols-[2fr_3fr] gap-4 items-start">
        {/* Left — build, then recent runs under the shock builder */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <div className="relative flex items-center gap-3">
              <label className="flex items-center gap-2 flex-1">
                <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
                  Name
                </span>
                <input
                  className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 flex-1"
                  placeholder="Untitled scenario"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <RunButton
                disabled={!canRun}
                running={mutation.isPending}
                onRun={() => mutation.mutate()}
              />
              {mutation.isPending && (
                <div
                  className="pointer-events-none absolute inset-x-0 -bottom-2 h-[3px] overflow-hidden rounded-full"
                  aria-hidden="true"
                >
                  <div className="h-full w-1/2 bg-gradient-to-r from-transparent via-accent-bright to-transparent scenario-sweep" />
                </div>
              )}
            </div>
            <ShockBuilder
              shocks={shocks}
              onChange={setShocks}
              instrument={instrument}
            />
            {mutation.isError && (
              <p className="text-xs text-down font-mono">
                Run failed: {mutation.error?.message ?? "unknown error"}
              </p>
            )}
          </div>
          <ScenarioHistoryList runs={initialRuns} />
        </div>

        {/* Right — impact globe, with the preview / narrated result beneath it. */}
        <div className="min-w-0 flex flex-col gap-4">
          <ScenarioGlobe shocks={shocks} instrument={instrument} />
          {lastResponse ? (
            <ResultPanel
              result={lastResponse.result}
              name={lastResponse.name}
              runId={lastResponse.run_id}
            />
          ) : (
            <ScenarioPreview shocks={shocks} />
          )}
        </div>
      </section>
    </div>
  );
}
