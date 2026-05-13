import { type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Size variant. `display` is for hero/cover treatments; `h1`/`h2`/`h3` for normal flow. */
  size?: "display" | "h1" | "h2" | "h3";
  className?: string;
  as?: "h1" | "h2" | "h3" | "h4" | "p" | "div";
}

const SIZE_CLASSES: Record<NonNullable<Props["size"]>, string> = {
  display: "text-[84px] leading-[0.94] tracking-[-0.025em]",
  h1: "text-[56px] leading-[0.96] tracking-[-0.02em]",
  h2: "text-[40px] leading-[1.02] tracking-[-0.015em]",
  h3: "text-[28px] leading-[1.08] tracking-[-0.01em]",
};

const SIZE_OPSZ: Record<NonNullable<Props["size"]>, number> = {
  display: 144,
  h1: 100,
  h2: 72,
  h3: 36,
};

/**
 * Fraunces serif display heading. Renders with the variable-font opsz axis tuned
 * to match the deck's heading scale, light weight, and tight negative tracking.
 *
 * Use <em> inside children to get italic + gold treatment via the GoldItalic
 * utility, or wrap a span manually with className="font-gold-italic".
 */
export function DisplayHeading({
  children,
  size = "h2",
  className = "",
  as: Tag = "h2",
}: Props) {
  return (
    <Tag
      className={`font-serif font-light text-ink-1 ${SIZE_CLASSES[size]} ${className}`}
      style={{ fontVariationSettings: `"opsz" ${SIZE_OPSZ[size]}, "SOFT" 30` }}
    >
      {children}
    </Tag>
  );
}
