/**
 * The four disciplines behind every ledger row (Phase A3). Static content —
 * each card is a method, not a claim, so no provenance labels are needed
 * here; the ledger below carries those.
 */
import { HelpTip } from "@/components/HelpTip";
import {
  Archive,
  FileCheck2,
  History,
  type LucideIcon,
  Scale,
} from "lucide-react";

const METHODS: {
  icon: LucideIcon;
  title: string;
  body: string;
  helpKey?: "preRegistered" | "walkForward" | "provenance";
}[] = [
  {
    icon: FileCheck2,
    title: "Pre-registered gates",
    body: "Every probe's pass/fail criteria are committed to the repository before the first run — results can't quietly move the goalposts.",
    helpKey: "preRegistered",
  },
  {
    icon: History,
    title: "Walk-forward only",
    body: "Every prediction sees strictly-past data. A cheating-model proof runs in CI to keep the chokepoint honest.",
    helpKey: "walkForward",
  },
  {
    icon: Archive,
    title: "Real-data provenance",
    body: "Synthetic results are never evidence. Each claim is labeled with the data that tested it — and untestable claims say so.",
    helpKey: "provenance",
  },
  {
    icon: Scale,
    title: "Bench and say so",
    body: "Models that fail their gate are retired publicly and kept in the ledger. Failures are findings, not embarrassments.",
  },
];

export function MethodStrip() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {METHODS.map(({ icon: Icon, title, body, helpKey }) => (
        <div
          key={title}
          className="card-interactive rounded-md border border-line-1 bg-surface-1 p-3"
        >
          <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-eyebrow text-accent">
            <Icon
              size={12}
              strokeWidth={1.5}
              aria-hidden="true"
              className="text-ink-4"
            />
            {title}
            {helpKey ? <HelpTip k={helpKey} className="ml-1" /> : null}
          </span>
          <p className="mt-2 text-[11px] leading-relaxed text-ink-3">{body}</p>
        </div>
      ))}
    </div>
  );
}
