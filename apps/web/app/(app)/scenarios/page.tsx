import { getScenarioRuns, getScenarioTemplates } from "../../../lib/api";
import { ScenariosShell } from "./ScenariosShell";
import type { RecentRun, ScenarioTemplate } from "./types";

export default async function ScenariosPage() {
  let templates: ScenarioTemplate[] = [];
  let runs: RecentRun[] = [];

  try {
    const tplResp = (await getScenarioTemplates()) as {
      templates: ScenarioTemplate[];
    };
    templates = tplResp.templates ?? [];
  } catch {
    // Server-side prefetch failed; render empty gallery
  }

  try {
    const runsResp = (await getScenarioRuns(20)) as { runs: RecentRun[] };
    runs = runsResp.runs ?? [];
  } catch {
    // Server-side prefetch failed; render empty history
  }

  return (
    <div className="flex flex-col h-full">
      <ScenariosShell initialTemplates={templates} initialRuns={runs} />
    </div>
  );
}
