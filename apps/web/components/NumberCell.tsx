interface Props {
  value: number;
  unit?: string;
  delta?: number;
  precision?: number;
}

export function NumberCell({ value, unit, delta, precision = 3 }: Props) {
  const formatted = value.toFixed(precision);

  let deltaEl: React.ReactNode = null;
  if (delta !== undefined) {
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
