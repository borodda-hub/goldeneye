import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
}

/**
 * Italic + gold-bright emphasis inside a serif heading.
 * Uses Fraunces with the SOFT axis pushed to 80 for the deck's "glowing italic"
 * effect. Pair with <DisplayHeading> as the surrounding text.
 */
export function GoldItalic({ children, className = "" }: Props) {
  return (
    <em
      className={`text-accent-bright not-italic ${className}`}
      style={{
        fontStyle: "italic",
        fontVariationSettings: '"opsz" 144, "SOFT" 80',
      }}
    >
      {children}
    </em>
  );
}
