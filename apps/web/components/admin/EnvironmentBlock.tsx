import { Cpu } from "lucide-react";

interface Props {
  gitSha?: string;
  buildTime?: string;
  envFlags: Record<string, boolean>;
}

export function EnvironmentBlock({ gitSha, buildTime, envFlags }: Props) {
  return (
    <div className="card-interactive border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2">
        <Cpu
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Environment
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 p-3 text-xs font-mono">
        <dt className="text-ink-3">git sha</dt>
        <dd className="text-ink-2 tabular-nums truncate">{gitSha ?? "—"}</dd>

        <dt className="text-ink-3">build time</dt>
        <dd className="text-ink-2 tabular-nums">{buildTime ?? "—"}</dd>

        {Object.entries(envFlags).map(([key, present]) => (
          <span key={key} className="contents">
            <dt className="text-ink-3">{key}</dt>
            <dd className={present ? "text-up" : "text-ink-4"}>
              {present ? "✓ set" : "○ unset"}
            </dd>
          </span>
        ))}
      </dl>
    </div>
  );
}
