/**
 * Verdict badge vocabulary for the validation ledger (Phase A3).
 *
 * Mirrors the desk VerdictBadge shape (rounded-sm bordered chip, 9px caps).
 * `no_edge` is deliberately rendered at full weight — failures are
 * first-class content on this page, never visually buried — while staying
 * factual (it labels a tested result, it does not alarm).
 */
import type { ValidationVerdict } from "@/lib/api";

const STYLES: Record<ValidationVerdict, { label: string; cls: string }> = {
  edge: { label: "edge · real-oos", cls: "border-up/40 bg-up/10 text-up" },
  no_edge: {
    label: "no edge · tested",
    cls: "border-down/40 bg-down/10 text-down",
  },
  promising: {
    label: "promising",
    cls: "border-conf-medium/40 bg-conf-medium/10 text-conf-medium",
  },
  insufficient: {
    label: "insufficient-n",
    cls: "border-line-2 bg-surface-2 text-ink-3",
  },
  collecting: {
    label: "collecting",
    cls: "border-cyan/40 bg-cyan/10 text-cyan",
  },
  benched: { label: "benched", cls: "border-line-1 text-ink-4" },
  methodology: { label: "methodology", cls: "border-line-1 text-ink-3" },
  unvalidated: {
    label: "unvalidated",
    cls: "border-conf-low/40 bg-conf-low/10 text-conf-low",
  },
};

export function VerdictTag({ verdict }: { verdict: ValidationVerdict }) {
  const s = STYLES[verdict] ?? STYLES.methodology;
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide ${s.cls}`}
    >
      {s.label}
    </span>
  );
}
