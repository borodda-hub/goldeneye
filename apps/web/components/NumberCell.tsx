import { FlashOnChange } from "./FlashOnChange";

interface Props {
  value: number | null | undefined;
  unit?: string;
  delta?: number | null;
  precision?: number;
  /** Briefly tint green/red when the value ticks. On by default; pass false
   *  for static figures that shouldn't draw the eye. */
  flash?: boolean;
}

/**
 * Renders a numeric value with optional unit and signed delta. Null / undefined
 * inputs render as an em-dash placeholder so a missing price (e.g. Yahoo hasn't
 * warmed up for a newly-listed contract) doesn't throw a TypeError on
 * `null.toFixed()` and crash the whole page.
 *
 * On a value change it flashes the classic terminal up/down tint (via
 * FlashOnChange — CSS, honors prefers-reduced-motion).
 */
export function NumberCell({
  value,
  unit,
  delta,
  precision = 3,
  flash = true,
}: Props) {
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

  const body = (
    <>
      {formatted}
      {unit && <span className="text-ink-3 ml-0.5 text-xs">{unit}</span>}
      {deltaEl}
    </>
  );

  if (!flash) {
    return <span className="font-mono tabular-nums text-ink-1">{body}</span>;
  }
  return (
    <FlashOnChange
      value={typeof value === "number" ? value : null}
      className="font-mono tabular-nums text-ink-1"
    >
      {body}
    </FlashOnChange>
  );
}
