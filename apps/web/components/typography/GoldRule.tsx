interface Props {
  /** Visual weight. `subtle` for section breaks, `bright` for emphasis. */
  variant?: "subtle" | "bright";
  className?: string;
}

/**
 * Horizontal hairline divider in the Goldeneye palette.
 * - `subtle` uses the deep gold (#8a6f3a) — for major section breaks
 * - `bright` uses the standard gold (#c9a35c) — for inline emphasis
 */
export function GoldRule({ variant = "subtle", className = "" }: Props) {
  const color = variant === "subtle" ? "border-accent-deep" : "border-accent";
  return <hr className={`border-0 border-t ${color} ${className}`} />;
}
