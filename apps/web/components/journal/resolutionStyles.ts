import type { ResolvedDirection } from "@/app/(app)/journal/types";

/**
 * Tailwind classes for the colored left-edge stripe on journal entry frames
 * (list row + detail drawer). Resolved entries get a 4px stripe in their
 * outcome color; unresolved + null share the neutral default.
 */
const RESOLUTION_STRIPE: Record<ResolvedDirection, string> = {
  hit: "border-l-4 border-l-up",
  miss: "border-l-4 border-l-down",
  neutral: "border-l-4 border-l-flat",
  unresolved: "border-l-4 border-l-conf-low",
};

const DEFAULT_STRIPE = ""; // null = no extra emphasis

export function resolutionStripeClass(
  resolved: ResolvedDirection | null,
): string {
  if (resolved === null) return DEFAULT_STRIPE;
  return RESOLUTION_STRIPE[resolved];
}

/** Short label used in aria-labels and badges ("Hit", "Miss", …). */
export function resolutionLabel(resolved: ResolvedDirection | null): string {
  if (resolved === null) return "Pending resolution";
  return resolved.charAt(0).toUpperCase() + resolved.slice(1);
}
