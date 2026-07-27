"use client";

/**
 * Load-bearing honesty label (B1 / S6). The signed-out calibration + journal
 * surfaces show the anonymous (NULL) pool, which is the seeded SAMPLE ANALYST —
 * a fictional analyst's decisions scored by the real engine on real prices. This
 * banner makes that unmistakable so the showcase is never read as a real analyst
 * track record. A signed-in user sees their own (empty-until-used) ledger, so the
 * banner is shown only when signed out (or when accounts are off — the demo).
 *
 * Issue #8: the claimed→realized figure is derived from the SAME live
 * calibration endpoint the page renders (AI_BEHAVIOR §sample_data_labeling —
 * a quoted figure must match what the page actually shows). We quote the
 * highest-conviction bucket only when it has a real sample (n ≥ 10) and the
 * miss is material; otherwise the sentence stays qualitative with no numbers.
 */

import { clerkEnabled } from "@/lib/clerk";
import { useCalibration } from "@/lib/queries";
import { SignedOut } from "@clerk/nextjs";
import { FlaskConical } from "lucide-react";

const MIN_RESOLVED = 10;
const MIN_GAP_PTS = 10;

/** The live overconfidence figure, or null when the data doesn't support one. */
function useOverconfidenceFigure(): {
  claimed: number;
  realized: number;
} | null {
  const { data } = useCalibration("NG", 5);
  if (!data) return null;
  // Highest-conviction bucket with a scoreable sample (buckets are ascending).
  const top = [...data.buckets]
    .reverse()
    .find(
      (b) =>
        b.claimed_mean !== null &&
        b.hit_rate !== null &&
        b.resolved_count >= MIN_RESOLVED,
    );
  if (!top || top.claimed_mean === null || top.hit_rate === null) return null;
  const claimed = Math.round(top.claimed_mean); // already a percent
  const realized = Math.round(top.hit_rate * 100); // fraction → percent
  if (claimed - realized < MIN_GAP_PTS) return null; // no material miss to point at
  return { claimed, realized };
}

function Banner() {
  const figure = useOverconfidenceFigure();
  return (
    <div
      role="note"
      className="flex items-start gap-3 border border-line-1 bg-surface-1 px-4 py-3"
    >
      <FlaskConical
        aria-hidden
        className="mt-0.5 h-4 w-4 shrink-0 text-accent"
      />
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[11px] uppercase tracking-eyebrow text-accent">
          Illustrative scenario
        </span>
        <p className="text-xs leading-relaxed text-ink-2">
          <span className="font-medium text-ink-1">
            Sample analyst · real engine · real prices.
          </span>{" "}
          A fictional sample analyst&rsquo;s decisions, scored by the same
          calibration engine against real market prices —{" "}
          <span className="text-ink-1">not a real analyst track record.</span>{" "}
          {figure ? (
            <>
              Notice her highest-conviction calls resolved far below what she
              claimed (~{figure.claimed}% claimed &rarr; ~{figure.realized}%
              realized): overconfidence that stays invisible until the engine
              scores it.
            </>
          ) : (
            <>
              Watch how her claimed conviction compares to what actually
              resolved: overconfidence stays invisible until the engine scores
              it.
            </>
          )}{" "}
          This is what calibration looks like in Goldeneye — point it at your
          desk and it scores your analysts the same way.
        </p>
      </div>
    </div>
  );
}

export function SampleDeskBanner() {
  // Accounts off (the open demo) → always the sample pool. Accounts on → only
  // when signed out (a signed-in user sees their own ledger, never the sample).
  if (!clerkEnabled) return <Banner />;
  return (
    <SignedOut>
      <Banner />
    </SignedOut>
  );
}
