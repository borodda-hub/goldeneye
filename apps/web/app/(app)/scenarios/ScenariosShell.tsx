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
import { useMutation } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { useState } from "react";
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

export function ScenariosShell({ initialTemplates, initialRuns }: Props) {
  const [selected, setSelected] = useState<ScenarioTemplate | null>(null);
  const [shocks, setShocks] = useState<Shock[]>([]);
  const [name, setName] = useState<string>("");
  const [lastResponse, setLastResponse] = useState<ScenarioRunResponse | null>(
    null,
  );

  const mutation = useMutation<ScenarioRunResponse, Error, void>({
    mutationFn: async () => {
      return (await runScenario({
        instrument: "NG",
        name: name.trim() || "Untitled scenario",
        shocks: shocks as unknown as Array<Record<string, unknown>>,
      })) as ScenarioRunResponse;
    },
    onSuccess: (data) => {
      setLastResponse(data);
      markStep("scenario");
    },
  });

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
        right={<HelpTip k="scenarioLab" />}
      />

      {/* Templates */}
      <section className="flex flex-col gap-2">
        <h2 className="font-mono text-[10px] text-accent uppercase tracking-widest">
          Templates
          <HelpTip k="templates" className="ml-1" />
        </h2>
        <TemplateGallery
          templates={initialTemplates}
          onSelect={loadTemplate}
          selectedId={selected?.id}
        />
      </section>

      {/* Build → impact: the workspace (left) sits next to the impact (right),
          which is always present — a live directional preview while you build,
          the full narrated result after a run — so the page never reads empty. */}
      <section className="grid grid-cols-1 xl:grid-cols-[2fr_3fr] gap-4 items-start">
        {/* Left — build */}
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
          <ShockBuilder shocks={shocks} onChange={setShocks} />
          {mutation.isError && (
            <p className="text-xs text-down font-mono">
              Run failed: {mutation.error?.message ?? "unknown error"}
            </p>
          )}
        </div>

        {/* Right — impact (always present) */}
        <div className="min-w-0">
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

      {/* History */}
      <section className="flex flex-col gap-2">
        <ScenarioHistoryList runs={initialRuns} />
      </section>
    </div>
  );
}
