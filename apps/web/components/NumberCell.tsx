interface Props {
  value: number | null | undefined;
  unit?: string;
  delta?: number | null;
  precision?: number;
}

/**
 * Renders a numeric value with optional unit and signed delta. Null / undefined
 * inputs render as an em-dash placeholder so a missing price (e.g. Yahoo hasn't
 * warmed up for a newly-listed contract) doesn't throw a TypeError on
 * `null.toFixed()` and crash the whole page.
 */
export function NumberCell({ value, unit, delta, precision = 3 }: Props) {
  const formatted =
    value === null || value === undefined ? "—" : value.toFixed(precision);

  let deltaEl: React.ReactNode = null;
  if (delta !== undefined && delta !== null) {
    if (delta > 0) {
      deltaEl = (
        <span className="text-up ml-1">
          ▲ {Math.abs(delta).toFixed(precision)}
        </span>
      );
    } else if (delta < 0) {
      deltaEl = (
        <span className="text-down ml-1">
          ▼ {Math.abs(delta).toFixed(precision)}
        </span>
      );
    } else {
      deltaEl = <span className="text-flat ml-1">—</span>;
    }
  }

  return (
    <span className="font-mono tabular-nums text-ink-1">
      {formatted}
      {unit && <span className="text-ink-3 ml-0.5 text-xs">{unit}</span>}
      {deltaEl}
    </span>
  );
}
