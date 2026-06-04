"use client";

import type { DqCoachingBucket, DqCoachingResponse } from "@/lib/api";
import { useDqCoaching } from "@/lib/queries";

interface Props {
  instrumentCode?: string;
}

function PatternList({
  items,
  emptyMessage,
  tone,
}: {
  items: string[];
  emptyMessage: string;
  tone: "supporting" | "failure";
}) {
  const dot = tone === "supporting" ? "bg-up" : "bg-down";
  if (items.length === 0) {
    return (
      <p className="text-xs text-ink-4 italic leading-relaxed">
        {emptyMessage}
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((item, i) => (
        <li
          key={`${tone}-${i}`}
          className="flex items-start gap-2 text-xs text-ink-2 leading-relaxed"
        >
          <span
            className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`}
            aria-hidden="true"
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function BucketCard({ bucket }: { bucket: DqCoachingBucket }) {
  return (
    <article className="border border-line-1 bg-surface-2 p-4 flex flex-col gap-3">
      <header className="flex items-baseline justify-between border-b border-line-1 pb-2">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Bucket {bucket.label}%
        </span>
      </header>

      <div className="flex flex-col gap-2">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          Effective patterns
        </span>
        <PatternList
          items={bucket.effective_patterns}
          emptyMessage="No effective patterns flagged."
          tone="supporting"
        />
      </div>

      <div className="flex flex-col gap-2">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          Failure patterns
        </span>
        <PatternList
          items={bucket.failure_patterns}
          emptyMessage="No failure patterns flagged."
          tone="failure"
        />
      </div>

      {bucket.recommendation ? (
        <div className="border-t border-line-1 pt-2">
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent-bright">
            Coach
          </span>
          <p className="text-xs text-ink-1 leading-relaxed mt-1">
            {bucket.recommendation}
          </p>
        </div>
      ) : null}
    </article>
  );
}

function EmptyState({ caveats }: { caveats: string[] }) {
  return (
    <div className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-3">
      <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
        <span
          aria-hidden="true"
          className="inline-block w-[18px] h-px bg-accent"
        />
        DQ Coach
      </span>
      <p className="text-sm text-ink-2 leading-relaxed">
        Coaching is unavailable until at least 3 journal entries have a resolved
        direction (Hit / Miss). Mark recent entries from the Journal page to
        unlock per-bucket analysis here.
      </p>
      {caveats.length > 0 ? (
        <ul className="flex flex-col gap-1 mt-1">
          {caveats.map((c, i) => (
            <li key={i} className="text-xs text-ink-4 leading-relaxed">
              • {c}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function DQCoachPanel({ instrumentCode = "NG" }: Props) {
  const { data, isLoading, error, refetch, isFetching } =
    useDqCoaching(instrumentCode);

  if (isLoading) {
    return (
      <section
        aria-label="DQ Coach"
        className="border border-line-1 bg-surface-1 p-5 text-sm text-ink-3 font-mono"
      >
        Synthesizing coaching…
      </section>
    );
  }

  if (error || !data) {
    return (
      <section
        aria-label="DQ Coach"
        className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-3"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          DQ Coach
        </span>
        <p className="text-sm text-down font-mono">
          Failed to load coaching. {error instanceof Error ? error.message : ""}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="self-start font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2.5 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1"
        >
          Retry
        </button>
      </section>
    );
  }

  const coaching: DqCoachingResponse = data;
  const hasBuckets = coaching.buckets.length > 0;
  const hasOverall =
    coaching.overall.synthesis || coaching.overall.top_recommendation;

  if (!hasBuckets && !hasOverall) {
    return <EmptyState caveats={coaching.safety.caveats} />;
  }

  return (
    <section aria-label="DQ Coach" className="flex flex-col gap-4">
      <div className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-3">
        <div className="flex items-baseline justify-between gap-3">
          <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
            <span
              aria-hidden="true"
              className="inline-block w-[18px] h-px bg-accent"
            />
            DQ Coach · Overall
          </span>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2 py-1 text-ink-3 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-50"
            aria-label="Re-run coaching"
          >
            {isFetching ? "…" : "↻"}
          </button>
        </div>

        {coaching.overall.synthesis ? (
          <p className="font-serif text-[18px] leading-snug text-ink-1 tracking-[-0.005em]">
            {coaching.overall.synthesis}
          </p>
        ) : (
          <p className="text-xs text-ink-4 italic">No overall synthesis yet.</p>
        )}

        {coaching.overall.top_recommendation ? (
          <div className="border-t border-line-1 pt-3">
            <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent-bright">
              Top recommendation
            </span>
            <p className="text-sm text-ink-1 leading-relaxed mt-1">
              {coaching.overall.top_recommendation}
            </p>
          </div>
        ) : null}
      </div>

      {hasBuckets ? (
        <div className="flex flex-col gap-3">
          {coaching.buckets.map((bucket) => (
            <BucketCard key={bucket.label} bucket={bucket} />
          ))}
        </div>
      ) : null}

      <p className="text-xs text-ink-4 italic leading-relaxed">
        {coaching.safety.disclaimer}
      </p>
    </section>
  );
}
