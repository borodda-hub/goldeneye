interface Props {
  contract: { code: string; expiry: string };
  resolution: string;
  asOf: string;
  dataSource?: string;
}

function formatAsOf(isoString: string): string {
  try {
    return isoString.split("T")[0];
  } catch {
    return isoString;
  }
}

export function ChartFooter({ contract, resolution, asOf, dataSource }: Props) {
  return (
    <div className="flex items-center gap-4 px-0 pt-2 border-t border-line-1 text-xs font-mono text-ink-3 shrink-0">
      <span>{contract.code}</span>
      <span className="text-ink-4">·</span>
      <span>expires {contract.expiry}</span>
      <span className="text-ink-4">·</span>
      <span>{resolution}</span>
      <span className="text-ink-4">·</span>
      <span>as of {formatAsOf(asOf)}</span>
      <span className="ml-auto text-ink-4">{dataSource ?? "market.mock"}</span>
    </div>
  );
}
