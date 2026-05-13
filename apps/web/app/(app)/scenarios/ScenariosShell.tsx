"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runScenario } from "@/lib/api";
import { TemplateGallery } from "@/components/scenarios/TemplateGallery";
import { ShockBuilder } from "@/components/scenarios/ShockBuilder";
import { RunButton } from "@/components/scenarios/RunButton";
import { ResultPanel } from "@/components/scenarios/ResultPanel";
import { ScenarioHistoryList } from "@/components/scenarios/ScenarioHistoryList";
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
    onSuccess: (data) => setLastResponse(data),
  });

  const loadTemplate = (t: ScenarioTemplate) => {
    setSelected(t);
    setShocks(t.shocks);
    setName(t.name);
    setLastResponse(null);
  };

  const canRun = shocks.length > 0 && !mutation.isPending;

  return (
    <div className="flex flex-col gap-4" data-tour="scenario-shell">
      {/* Header */}
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-ink-1">Scenario Lab</h1>
        <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
          Counterfactual model rerun
        </span>
      </div>

      {/* Templates */}
      <section className="flex flex-col gap-2">
        <h2 className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Templates
        </h2>
        <TemplateGallery
          templates={initialTemplates}
          onSelect={loadTemplate}
          selectedId={selected?.id}
        />
      </section>

      {/* Builder + run */}
      <section className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 flex-1">
            <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
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
        </div>
        <ShockBuilder shocks={shocks} onChange={setShocks} />
        {mutation.isError && (
          <p className="text-xs text-down font-mono">
            Run failed: {mutation.error?.message ?? "unknown error"}
          </p>
        )}
      </section>

      {/* Result */}
      {lastResponse && (
        <section>
          <ResultPanel
            result={lastResponse.result}
            name={lastResponse.name}
            runId={lastResponse.run_id}
          />
        </section>
      )}

      {/* History */}
      <section className="flex flex-col gap-2">
        <ScenarioHistoryList runs={initialRuns} />
      </section>
    </div>
  );
}
