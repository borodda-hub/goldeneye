"use client";

/**
 * Load-bearing honesty label (B1 / S6). The signed-out calibration + journal
 * surfaces show the anonymous (NULL) pool, which is the seeded SAMPLE ANALYST —
 * a fictional analyst's decisions scored by the real engine on real prices. This
 * banner makes that unmistakable so the showcase is never read as a real analyst
 * track record. A signed-in user sees their own (empty-until-used) ledger, so the
 * banner is shown only when signed out (or when accounts are off — the demo).
 */

import { clerkEnabled } from "@/lib/clerk";
import { SignedOut } from "@clerk/nextjs";
import { FlaskConical } from "lucide-react";

function Banner() {
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
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Illustrative scenario
        </span>
        <p className="text-xs leading-relaxed text-ink-2">
          <span className="font-medium text-ink-1">
            Sample analyst · real engine · real prices.
          </span>{" "}
          A fictional sample analyst&rsquo;s decisions, scored by the same
          calibration engine against real market prices —{" "}
          <span className="text-ink-1">not a real analyst track record.</span>{" "}
          Notice her highest-conviction calls resolved far below what she
          claimed (~87% claimed &rarr; ~29% realized): overconfidence that stays
          invisible until the engine scores it. This is what calibration looks
          like in Goldeneye — point it at your desk and it scores your analysts
          the same way.
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
