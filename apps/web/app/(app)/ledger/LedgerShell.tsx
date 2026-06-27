"use client";

import {
  ChevronDown,
  ChevronRight,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { PageHeader } from "../../../components/PageHeader";
import {
  asBool,
  asNumber,
  asRecord,
  asString,
  decisionHypothesis,
  decisionTimestamp,
  fmtDateTime,
  fmtFraction,
  fmtPrice,
} from "./format";
import type { LedgerDecision, LedgerEvent } from "./types";

interface Props {
  initialDecisions: LedgerDecision[];
}

const OUTCOME_CLASS: Record<string, string> = {
  hit: "text-up",
  miss: "text-down",
  neutral: "text-flat",
};

function IntegrityBadge({ decision }: { decision: LedgerDecision }) {
  if (decision.chain_ok) {
    return (
      <span className="inline-flex items-center gap-1 rounded-sm border border-up/40 bg-up-soft px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-up">
        <ShieldCheck size={11} strokeWidth={1.75} aria-hidden="true" />
        Verified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-sm border border-down/40 bg-down-soft px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-down">
      <ShieldAlert size={11} strokeWidth={1.75} aria-hidden="true" />
      Tamper detected (seq {decision.broken_at_seq})
    </span>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[9px] uppercase tracking-wider text-ink-4">
        {label}
      </span>
      <span className="text-[12px] text-ink-1 tabular-nums">{value}</span>
    </div>
  );
}

function CreatedEvent({ event }: { event: LedgerEvent }) {
  const payload = asRecord(event.payload);
  const inputs = asRecord(payload.user_inputs);
  const sys = asRecord(payload.system_context);
  const captured = asBool(sys.captured) === true;
  const ensemble = asRecord(sys.ensemble);
  const lineup = Array.isArray(sys.model_lineup) ? sys.model_lineup : [];

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="mb-1.5 font-mono text-[9px] uppercase tracking-wider text-ink-4">
          What you decided
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
          <Field
            label="Direction"
            value={asString(inputs.predicted_direction) ?? "—"}
          />
          <Field
            label="Confidence"
            value={
              asNumber(inputs.confidence_pct) !== null
                ? `${asNumber(inputs.confidence_pct)}%`
                : "—"
            }
          />
          <Field
            label="Horizon"
            value={
              asNumber(inputs.horizon_days) !== null
                ? `${asNumber(inputs.horizon_days)}d`
                : "—"
            }
          />
          <Field
            label="Threshold"
            value={
              asNumber(inputs.threshold_pct) !== null
                ? `${asNumber(inputs.threshold_pct)}%`
                : "—"
            }
          />
          <Field
            label="Anchor"
            value={fmtPrice(asNumber(inputs.anchor_price))}
          />
          <Field
            label="Conviction"
            value={
              asNumber(inputs.thesis_conviction_at_write) !== null
                ? `${asNumber(inputs.thesis_conviction_at_write)}%`
                : "—"
            }
          />
        </div>
      </div>

      <div>
        <p className="mb-1.5 font-mono text-[9px] uppercase tracking-wider text-ink-4">
          What the system knew
        </p>
        {captured ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
            <Field
              label="Ensemble"
              value={asString(ensemble.direction) ?? "—"}
            />
            <Field
              label="Agreement"
              value={asString(ensemble.agreement) ?? "—"}
            />
            <Field
              label="Vol regime"
              value={asString(ensemble.vol_regime) ?? "—"}
            />
            <Field
              label="Models"
              value={lineup.length > 0 ? lineup.join(", ") : "—"}
            />
          </div>
        ) : (
          // Honest recorded-absence — the audit trail shows THAT it didn't know,
          // and why, rather than silently omitting the context.
          <p className="rounded-sm border border-line-1 bg-surface-0 px-2.5 py-1.5 text-[11px] text-ink-3">
            System context not captured —{" "}
            <span className="text-ink-2">
              {asString(sys.reason) ?? "reason unavailable"}
            </span>
          </p>
        )}
      </div>
    </div>
  );
}

function ResolvedEvent({ event }: { event: LedgerEvent }) {
  const p = asRecord(event.payload);
  const outcome = asString(p.outcome) ?? "—";
  const cls = OUTCOME_CLASS[outcome] ?? "text-ink-1";
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[9px] uppercase tracking-wider text-ink-4">
          Outcome
        </span>
        <span className={`text-[12px] font-medium capitalize ${cls}`}>
          {outcome}
        </span>
      </div>
      <Field label="Realized" value={fmtPrice(asNumber(p.realized_close))} />
      <Field label="Anchor" value={fmtPrice(asNumber(p.anchor_price))} />
      <Field label="Move" value={fmtFraction(asNumber(p.move_pct))} />
      <Field
        label="Resolved by"
        value={asBool(p.auto_resolved) === true ? "engine" : "manual"}
      />
    </div>
  );
}

function AmendedEvent({ event }: { event: LedgerEvent }) {
  const p = asRecord(event.payload);
  const field = asString(p.field) ?? "field";
  const old = p.old == null ? "∅" : String(p.old);
  const next = p.new == null ? "∅" : String(p.new);
  return (
    <p className="text-[12px] text-ink-2">
      <span className="font-mono text-ink-3">{field}</span>:{" "}
      <span className="text-ink-4 line-through">{old}</span>{" "}
      <span className="text-ink-4">→</span>{" "}
      <span className="text-ink-1">{next}</span>
    </p>
  );
}

const EVENT_LABEL: Record<string, string> = {
  created: "Decided",
  resolved: "Resolved",
  amended: "Amended",
};

function EventRow({ event }: { event: LedgerEvent }) {
  return (
    <div className="relative border-l border-line-2 pl-4">
      <span
        aria-hidden="true"
        className="absolute -left-[3px] top-1.5 h-1.5 w-1.5 rounded-full bg-accent"
      />
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-accent">
          {EVENT_LABEL[event.event_type] ?? event.event_type}
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {fmtDateTime(event.occurred_at)}
        </span>
      </div>
      {event.event_type === "created" && <CreatedEvent event={event} />}
      {event.event_type === "resolved" && <ResolvedEvent event={event} />}
      {event.event_type === "amended" && <AmendedEvent event={event} />}
    </div>
  );
}

function DecisionCard({ decision }: { decision: LedgerDecision }) {
  const [open, setOpen] = useState(false);
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <div className="border border-line-1 bg-surface-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-surface-2"
        aria-expanded={open}
      >
        <Chevron
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          className="shrink-0 text-ink-4"
        />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="line-clamp-1 text-sm text-ink-1">
            {decisionHypothesis(decision)}
          </p>
          <span className="font-mono text-[10px] text-ink-4 tabular-nums">
            {fmtDateTime(decisionTimestamp(decision))} ·{" "}
            {decision.events.length} event
            {decision.events.length === 1 ? "" : "s"}
          </span>
        </div>
        <IntegrityBadge decision={decision} />
      </button>
      {open && (
        <div className="flex flex-col gap-4 border-t border-line-1 px-4 py-4">
          {decision.events.map((e) => (
            <EventRow key={e.seq} event={e} />
          ))}
        </div>
      )}
    </div>
  );
}

export function LedgerShell({ initialDecisions }: Props) {
  const decisions = initialDecisions;

  return (
    <div className="stagger flex flex-col gap-4">
      <PageHeader
        icon={ScrollText}
        title="Decision Ledger"
        subtitle="Immutable audit trail · what you knew at decision"
      />

      <p className="max-w-3xl text-[12px] leading-relaxed text-ink-3">
        A tamper-evident, append-only record of every decision and its
        lifecycle. Each entry hash-chains off the last, so any out-of-band edit
        is detected ("Verified" vs "Tamper detected"). The record accrues from
        this feature forward only — decisions made before it have no ledger
        entry by design (history is never reconstructed after the fact).
      </p>

      {decisions.length === 0 ? (
        <div className="border border-line-1 bg-surface-1 p-4">
          <div className="flex flex-col items-center gap-1.5 py-8 text-ink-4">
            <ScrollText size={18} strokeWidth={1.5} aria-hidden="true" />
            <span className="text-[11px]">No ledgered decisions yet</span>
            <span className="text-[10px] text-ink-4/70">
              Log a structured decision in the Journal to start the trail.
            </span>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {decisions.map((d) => (
            <DecisionCard key={d.decision_id} decision={d} />
          ))}
        </div>
      )}
    </div>
  );
}
