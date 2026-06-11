"use client";

import type { DeskAnalyst, SkillVerdict } from "@/lib/api";
import { useDeskCalibration } from "@/lib/queries";
import { Users } from "lucide-react";

/** Brier: lower = better-calibrated; 0.25 ≈ a 50/50 coin flip. */
function brierColor(b: number | null): string {
  if (b === null) return "text-ink-4";
  if (b <= 0.2) return "text-up";
  if (b <= 0.25) return "text-conf-medium";
  return "text-down";
}

function label(userId: string | null): string {
  if (!userId) return "Unattributed desk";
  return `Analyst ${userId.slice(0, 6)}`;
}

function gapTone(gap: number | null): { text: string; cls: string } {
  if (gap === null) return { text: "—", cls: "text-ink-4" };
  if (gap > 5) return { text: `+${gap} overconfident`, cls: "text-down" };
  if (gap < -5) return { text: `${gap} underconfident`, cls: "text-up" };
  return { text: "calibrated", cls: "text-ink-4" };
}

/** The skill-vs-luck verdict — a badge, intentionally understated for `luck`
 * (it is "not distinguishable from chance," never an accusation of guessing). */
function VerdictBadge({ verdict }: { verdict: SkillVerdict }) {
  const styles: Record<SkillVerdict, { text: string; cls: string }> = {
    skill: {
      text: "Skill",
      cls: "border-up/40 bg-up/10 text-up",
    },
    luck: {
      text: "Luck",
      cls: "border-line-1 text-ink-3",
    },
    insufficient: {
      text: "Insufficient",
      cls: "border-line-1 text-ink-4",
    },
  };
  const s = styles[verdict];
  return (
    <span
      className={`inline-block rounded-sm border px-1.5 py-0.5 text-[9px] uppercase tracking-wide ${s.cls}`}
    >
      {s.text}
    </span>
  );
}

function Row({ a, rank }: { a: DeskAnalyst; rank: number }) {
  const gap = gapTone(a.calibration_gap);
  const hitPct = a.hit_rate === null ? null : Math.round(a.hit_rate * 100);
  const ci =
    a.wilson_low !== null && a.wilson_high !== null
      ? `[${Math.round(a.wilson_low * 100)}–${Math.round(a.wilson_high * 100)}%]`
      : null;
  return (
    <tr className={`border-t border-line-1 ${a.qualifies ? "" : "opacity-50"}`}>
      <td className="py-1.5 pr-2 font-mono text-ink-4 tabular-nums">
        {a.qualifies ? rank : "—"}
      </td>
      <td className="py-1.5 pr-2 text-ink-1">{label(a.user_id)}</td>
      <td className="py-1.5 pr-2">
        <VerdictBadge verdict={a.verdict} />
      </td>
      <td className="py-1.5 pr-2 text-right tabular-nums text-ink-2">
        {hitPct === null ? (
          "—"
        ) : (
          <span>
            {hitPct}%{" "}
            {ci && <span className="text-[9px] text-ink-4">{ci}</span>}
          </span>
        )}
      </td>
      <td className="py-1.5 pr-2 text-right tabular-nums">
        {a.qualifies ? (
          <span className={`text-sm ${brierColor(a.brier)}`}>
            {a.brier === null ? "—" : a.brier.toFixed(3)}
          </span>
        ) : (
          <span className="text-[10px] text-ink-4">
            need {Math.max(0, 10 - a.n)} more
          </span>
        )}
      </td>
      <td className="py-1.5 pr-2 text-right tabular-nums text-ink-3">
        {a.mean_conviction === null ? "—" : `${Math.round(a.mean_conviction)}%`}
      </td>
      <td className={`py-1.5 pr-2 text-right text-[10px] ${gap.cls}`}>
        {gap.text}
      </td>
      <td className="py-1.5 text-right tabular-nums text-ink-4">{a.n}</td>
    </tr>
  );
}

export function DeskCalibrationCard() {
  const { data, isLoading } = useDeskCalibration();
  const analysts = data?.analysts ?? [];
  const baselinePct = Math.round((data?.baseline ?? 0.5) * 100);

  return (
    <section className="card-interactive border border-line-1 bg-surface-1 p-3 flex flex-col gap-2.5">
      <h2 className="flex items-center gap-2 font-mono text-[10px] text-ink-3 uppercase tracking-widest">
        <Users size={12} strokeWidth={1.5} aria-hidden="true" />
        Desk Calibration · skill vs. luck
      </h2>

      {isLoading ? (
        <p className="text-[10px] text-ink-4 font-mono">Loading…</p>
      ) : analysts.length === 0 ? (
        <p className="text-[10px] text-ink-4 font-mono">
          No resolved decisions yet — calibration appears as decisions resolve.
        </p>
      ) : (
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-[9px] uppercase tracking-widest text-ink-4 text-left">
              <th className="font-normal pr-2">#</th>
              <th className="font-normal pr-2">Analyst</th>
              <th className="font-normal pr-2">Verdict</th>
              <th className="font-normal pr-2 text-right">Hit · 95% CI</th>
              <th className="font-normal pr-2 text-right">Calibration</th>
              <th className="font-normal pr-2 text-right">Conv</th>
              <th className="font-normal pr-2 text-right">Bias</th>
              <th className="font-normal text-right">n</th>
            </tr>
          </thead>
          <tbody>
            {analysts.map((a, i) => (
              <Row key={a.user_id ?? "unattributed"} a={a} rank={i + 1} />
            ))}
          </tbody>
        </table>
      )}

      <p className="text-[9px] text-ink-4 font-mono leading-relaxed">
        <span className="text-ink-3">Verdict</span> is the test that separates
        skill from luck — and correctly refuses to call noise skill. We take
        each desk's directional hit-rate and ask whether its 95% confidence
        interval clears a coin flip ({baselinePct}%):{" "}
        <span className="text-ink-3">Skill</span> = the lower bound beats chance
        on this sample; <span className="text-ink-3">Luck</span> = not yet
        distinguishable from chance (a hot streak isn't proof);{" "}
        <span className="text-ink-3">Insufficient</span> = fewer than{" "}
        {data?.min_resolved ?? 10} resolved calls. The blind random desk lands
        on Luck by design — that's the test working.{" "}
        <span className="text-ink-3">Calibration</span> (Brier on stated
        conviction) separately measures whether confidence is reliable.
        Descriptive decision-quality diagnostics, not advice.
      </p>
    </section>
  );
}
