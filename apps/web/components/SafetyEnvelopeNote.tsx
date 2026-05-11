"use client";

import { useState } from "react";
import { DirectionChip } from "./DirectionChip";

interface Envelope {
  confidence: string;
  caveats: string[];
  as_of: string;
  disclaimer: string;
}

interface Props {
  envelope: Envelope;
}

function isDirection(s: string): s is "bullish" | "bearish" | "neutral" {
  return s === "bullish" || s === "bearish" || s === "neutral";
}

export function SafetyEnvelopeNote({ envelope }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="text-xs text-ink-3 border border-line-1 rounded-md p-2">
      <button
        type="button"
        className="flex items-center gap-2 w-full text-left"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {isDirection(envelope.confidence) ? (
          <DirectionChip direction={envelope.confidence} />
        ) : (
          <span className="font-medium capitalize">{envelope.confidence}</span>
        )}
        <span className="text-ink-4">as of {envelope.as_of}</span>
        <span className="ml-auto">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-1">
          {envelope.caveats.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5">
              {envelope.caveats.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
          <p className="text-ink-4 mt-1">{envelope.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
