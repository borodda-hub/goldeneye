/**
 * THE LEDGER (Phase A3) — every claim the platform makes about its models,
 * with verdict, provenance, and evidence. Rows arrive from
 * `GET /v1/validation`, whose content is CI-drift-locked to
 * `docs/MODEL_DILIGENCE.md` — this table cannot say something the claims
 * ledger doesn't.
 *
 * Display order is the API's: the validated edge first, then the no-edge
 * family at full visual weight (failures are the credibility, not the
 * fine print), then promising/parked, collecting, methodology.
 */
import { HelpTip } from "@/components/HelpTip";
import type { ValidationLedgerRow } from "@/lib/api";
import { VerdictTag } from "./VerdictTag";

export function ValidationLedgerTable({
  rows,
}: { rows: ValidationLedgerRow[] }) {
  return (
    <div className="card-interactive rounded-md border border-line-1 bg-surface-1 px-4 py-4">
      <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
        The validation ledger
        <HelpTip k="provenance" className="ml-1" />
      </span>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[9px] uppercase tracking-widest text-ink-4">
              <th className="py-1.5 pr-3 font-normal">Verdict</th>
              <th className="py-1.5 pr-2 font-normal">Claim & result</th>
              <th className="py-1.5 pr-2 font-normal">
                Provenance
                <HelpTip k="realOos" className="ml-1" />
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-t border-line-1 align-top">
                <td className="py-2.5 pr-3">
                  <VerdictTag verdict={r.verdict} />
                </td>
                <td className="max-w-xl py-2.5 pr-2">
                  <p className="text-xs font-medium text-ink-1">{r.claim}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-ink-3">
                    {r.summary}
                  </p>
                  <p className="mt-1.5 font-mono text-[9px] leading-relaxed text-ink-4">
                    {r.evidence}
                    <span className="text-ink-4"> · gate: </span>
                    <span className="text-ink-3">{r.gate_ref}</span>
                    <span className="text-ink-4"> · {r.updated}</span>
                  </p>
                </td>
                <td className="whitespace-nowrap py-2.5 pr-2 font-mono text-[10px] text-ink-3">
                  {r.provenance}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 border-t border-line-1 pt-2 font-mono text-[9px] leading-relaxed text-ink-4">
        Every row mirrors{" "}
        <span className="text-ink-3">docs/MODEL_DILIGENCE.md</span> — a CI test
        fails the build if this page and the claims ledger ever disagree.
        Verdicts come from pre-registered gates; sample sizes are quoted as
        non-overlapping effective counts
        <HelpTip k="nEff" className="ml-1" />. Descriptive research diligence,
        not advice.
      </p>
    </div>
  );
}
