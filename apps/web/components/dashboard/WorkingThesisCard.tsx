"use client";

import { CollapseToggle } from "@/components/CollapseToggle";
import { HelpTip } from "@/components/HelpTip";
import { SkeletonText } from "@/components/Skeleton";
import type {
  Thesis,
  ThesisCritique,
  ThesisDevilsAdvocate,
  ThesisSeed,
} from "@/lib/api";
import { markStep } from "@/lib/onboarding";
import {
  useCreateThesis,
  useCritiqueThesis,
  useCurrentThesis,
  useDevilsAdvocate,
  usePatchThesis,
  useThesisSeed,
} from "@/lib/queries";
import { useCollapsed } from "@/lib/useCollapsed";
import { useState } from "react";
import { DevilsAdvocateDrawer } from "./DevilsAdvocateDrawer";
import { ThesisCritiqueDrawer } from "./ThesisCritiqueDrawer";
import { ThesisEditModal } from "./ThesisEditModal";

const EMPTY_SEED: ThesisSeed = {
  instrument_code: "NG",
  statement: "",
  supporting_evidence: [],
  contradicting_evidence: [],
  missing_data: [],
  conviction_pct: 50,
};

function relativeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const mins = Math.floor((now - then) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toISOString().slice(0, 10);
}

function ReadView({
  thesis,
  onEdit,
  onCritique,
  critiqueLoading,
  onDevilsAdvocate,
  devilsLoading,
}: {
  thesis: Thesis;
  onEdit: () => void;
  onCritique: () => void;
  critiqueLoading: boolean;
  onDevilsAdvocate: () => void;
  devilsLoading: boolean;
}) {
  return (
    <div className="flex flex-col gap-3">
      {/* Statement */}
      <p className="font-serif text-[22px] leading-snug text-ink-1 tracking-[-0.01em]">
        <span className="italic text-accent-bright">&ldquo;</span>
        {thesis.statement}
        <span className="italic text-accent-bright">&rdquo;</span>
      </p>

      {/* Conviction + meta */}
      <div className="flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
            Conviction
          </span>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-28 bg-surface-2 overflow-hidden">
              <div
                className="h-full bg-accent"
                style={{ width: `${thesis.conviction_pct}%` }}
              />
            </div>
            <span className="font-mono tabular-nums text-sm text-accent-bright">
              {thesis.conviction_pct}%
            </span>
          </div>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 ml-auto">
          Updated · {relativeAgo(thesis.updated_at)}
        </span>
      </div>

      {/* Counts */}
      <div className="flex items-center gap-6 border-t border-line-1 pt-3">
        <CountBlock
          label="Supporting"
          n={thesis.supporting_evidence.length}
          tone="supporting"
        />
        <CountBlock
          label="Contradicting"
          n={thesis.contradicting_evidence.length}
          tone="contradicting"
        />
        <CountBlock
          label="Missing data"
          n={thesis.missing_data.length}
          tone="missing"
        />
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={onCritique}
            disabled={critiqueLoading}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2.5 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-50"
          >
            {critiqueLoading ? "…" : "→ Critique"}
          </button>
          <button
            type="button"
            onClick={onDevilsAdvocate}
            disabled={devilsLoading}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2.5 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-50"
          >
            {devilsLoading ? "…" : "→ Devil's Advocate"}
          </button>
          <button
            type="button"
            onClick={onEdit}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2.5 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1"
          >
            ⚙ Edit
          </button>
        </div>
      </div>
    </div>
  );
}

function CountBlock({
  label,
  n,
  tone,
}: {
  label: string;
  n: number;
  tone: "supporting" | "contradicting" | "missing";
}) {
  const dot: Record<typeof tone, string> = {
    supporting: "bg-up",
    contradicting: "bg-down",
    missing: "bg-accent-deep",
  };
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${dot[tone]}`}
        aria-hidden="true"
      />
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
        {label}
      </span>
      <span className="font-mono tabular-nums text-sm text-ink-1">{n}</span>
    </div>
  );
}

function EmptyView({ onDraft }: { onDraft: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3">
      <p className="text-sm text-ink-3 leading-relaxed max-w-2xl">
        No working thesis yet. Draft one from the latest forecast and scenario
        signals, then refine it. The thesis anchors your journal entries and
        feeds calibration tracking.
      </p>
      <button
        type="button"
        onClick={onDraft}
        className="font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-3 py-1.5 text-accent-bright hover:bg-accent hover:text-bg"
      >
        ↑ Draft a thesis
      </button>
    </div>
  );
}

export function WorkingThesisCard({
  instrumentCode = "NG",
}: {
  instrumentCode?: string;
}) {
  const { data: thesis, isLoading } = useCurrentThesis(instrumentCode);
  const [editOpen, setEditOpen] = useState(false);
  const [seedFetching, setSeedFetching] = useState(false);
  const { collapsed, toggle } = useCollapsed(
    "goldeneye:dashboard:working-thesis-collapsed",
    true, // default collapsed so a fresh dashboard fits on one screen
  );
  const seedQ = useThesisSeed(instrumentCode, seedFetching);
  const createMut = useCreateThesis(instrumentCode);
  const patchMut = usePatchThesis(instrumentCode);
  const critiqueMut = useCritiqueThesis();
  const [critique, setCritique] = useState<ThesisCritique | null>(null);
  const [critiqueOpen, setCritiqueOpen] = useState(false);
  const [critiqueError, setCritiqueError] = useState<string | null>(null);
  const devilsMut = useDevilsAdvocate();
  const [devils, setDevils] = useState<ThesisDevilsAdvocate | null>(null);
  const [devilsOpen, setDevilsOpen] = useState(false);
  const [devilsError, setDevilsError] = useState<string | null>(null);

  async function handleSave(next: {
    statement: string;
    supporting_evidence: typeof EMPTY_SEED.supporting_evidence;
    contradicting_evidence: typeof EMPTY_SEED.contradicting_evidence;
    missing_data: string[];
    conviction_pct: number;
  }) {
    try {
      if (thesis) {
        await patchMut.mutateAsync({ id: thesis.id, body: next });
      } else {
        await createMut.mutateAsync({
          instrument_code: instrumentCode,
          ...next,
        });
      }
      setEditOpen(false);
      setSeedFetching(false);
      markStep("thesis");
    } catch {
      // Mutation hooks expose error state; modal will re-render.
    }
  }

  async function handleCritique() {
    if (!thesis) return;
    setCritiqueOpen(true);
    setCritique(null);
    setCritiqueError(null);
    try {
      const result = await critiqueMut.mutateAsync(thesis.id);
      setCritique(result);
    } catch (err) {
      setCritiqueError(
        err instanceof Error ? err.message : "Failed to fetch critique.",
      );
    }
  }

  async function handleDevilsAdvocate() {
    if (!thesis) return;
    setDevilsOpen(true);
    setDevils(null);
    setDevilsError(null);
    try {
      setDevils(await devilsMut.mutateAsync(thesis.id));
    } catch (err) {
      setDevilsError(
        err instanceof Error ? err.message : "Failed to run Devil's Advocate.",
      );
    }
  }

  function handleDraft() {
    setSeedFetching(true);
    setEditOpen(true);
  }

  // Pick the right initial form values: existing thesis, or fetched seed,
  // or empty seed (fallback while seed is still loading).
  const initialForModal = thesis
    ? thesis
    : seedFetching && seedQ.data
      ? seedQ.data
      : EMPTY_SEED;

  const saving = createMut.isPending || patchMut.isPending;
  const saveError = (createMut.error || patchMut.error) as Error | null;

  return (
    <div
      className="card-interactive border border-line-1 bg-surface-1 px-5 py-4 flex flex-col gap-3"
      data-tour="working-thesis"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          <span
            aria-hidden="true"
            className="inline-block w-[18px] h-px bg-accent"
          />
          Working Thesis · {instrumentCode}
          <HelpTip k="workingThesis" className="ml-1" />
        </span>
        <CollapseToggle
          collapsed={collapsed}
          onToggle={toggle}
          label="Working thesis"
        />
      </div>

      {collapsed ? null : isLoading ? (
        <div data-testid="thesis-loading">
          <SkeletonText lines={3} />
        </div>
      ) : thesis ? (
        <ReadView
          thesis={thesis}
          onEdit={() => setEditOpen(true)}
          onCritique={handleCritique}
          critiqueLoading={critiqueMut.isPending}
          onDevilsAdvocate={handleDevilsAdvocate}
          devilsLoading={devilsMut.isPending}
        />
      ) : (
        <EmptyView onDraft={handleDraft} />
      )}

      <ThesisEditModal
        open={editOpen}
        initial={initialForModal}
        saving={saving}
        error={saveError?.message ?? null}
        onClose={() => {
          setEditOpen(false);
          setSeedFetching(false);
        }}
        onSave={handleSave}
      />
      <ThesisCritiqueDrawer
        open={critiqueOpen}
        loading={critiqueMut.isPending}
        error={critiqueError}
        critique={critique}
        onClose={() => setCritiqueOpen(false)}
      />
      <DevilsAdvocateDrawer
        open={devilsOpen}
        loading={devilsMut.isPending}
        error={devilsError}
        review={devils}
        onClose={() => setDevilsOpen(false)}
      />
    </div>
  );
}
