interface SkeletonProps {
  /** Tailwind sizing/layout classes for the placeholder block. */
  className?: string;
}

/**
 * A single shimmering placeholder block. Reuses the gold `.skeleton` sweep from
 * globals.css (reduced-motion → static muted block). Compose several to mock a
 * card/table shape while data loads, instead of a bare "Loading…" string.
 */
export function Skeleton({ className = "" }: SkeletonProps) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

/** A stack of shimmer lines; the last line is shortened like real text. */
export function SkeletonText({ lines = 3, className = "" }: SkeletonTextProps) {
  return (
    <div className={`flex flex-col gap-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton
          // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length set of identical placeholders, no stable id
          key={i}
          className={`h-3 ${i === lines - 1 ? "w-2/3" : "w-full"}`}
        />
      ))}
    </div>
  );
}
