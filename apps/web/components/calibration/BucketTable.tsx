import type { CalibrationBucket } from "@/lib/api";

interface Props {
  buckets: CalibrationBucket[];
}

function fmtPct(v: number | null, digits = 0): string {
  if (v === null) return "—";
  return `${v.toFixed(digits)}%`;
}

function fmtPctFromFraction(v: number | null): string {
  if (v === null) return "—";
  return `${(v * 100).toFixed(0)}%`;
}

export function BucketTable({ buckets }: Props) {
  return (
    <section
      aria-label="Calibration buckets"
      className="border border-line-1 bg-surface-1 p-5 flex flex-col gap-3"
    >
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
        Per-bucket detail
      </span>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="border-b border-line-1 text-ink-3">
            <tr className="text-left">
              <Th>Bucket</Th>
              <Th align="right">Claimed mean</Th>
              <Th align="right">Total n</Th>
              <Th align="right">Resolved</Th>
              <Th align="right">Hits</Th>
              <Th align="right">Hit rate</Th>
            </tr>
          </thead>
          <tbody>
            {buckets.map((b) => (
              <tr
                key={b.label}
                className="border-b border-line-1/40 last:border-b-0 hover:bg-surface-2/40"
              >
                <Td>
                  <span className="font-mono text-ink-1">{b.label}%</span>
                </Td>
                <Td align="right">{fmtPct(b.claimed_mean)}</Td>
                <Td align="right">{b.total_count}</Td>
                <Td align="right">{b.resolved_count}</Td>
                <Td align="right">{b.hit_count}</Td>
                <Td align="right">
                  {b.hit_rate === null ? (
                    <span className="text-ink-4">
                      n={b.resolved_count} (need 3+)
                    </span>
                  ) : (
                    <span className="text-accent-bright font-medium">
                      {fmtPctFromFraction(b.hit_rate)}
                    </span>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Th({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <th
      className={`px-3 py-2 font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 text-${align}`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <td className={`px-3 py-2 font-mono tabular-nums text-ink-2 text-${align}`}>
      {children}
    </td>
  );
}
