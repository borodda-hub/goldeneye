"use client";

import type { AiThesis, Instrument } from "@/app/(app)/dashboard/types";
import { CollapseToggle } from "@/components/CollapseToggle";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";
import { useCollapsed } from "@/lib/useCollapsed";

interface Props {
  instrument: Instrument;
  thesis: AiThesis;
}

const CURVE_LABEL: Record<AiThesis["curve_shape"], string> = {
  contango: "Contango",
  backwardation: "Backwardation",
  mixed: "Mixed curve",
  unknown: "Curve —",
};

export function AiThesisCard({ instrument, thesis }: Props) {
  const hasThesis = thesis.thesis.length > 0;
  const hasLists = thesis.drivers.length > 0 || thesis.watch.length > 0;
  const { collapsed, toggle } = useCollapsed(
    "goldeneye:dashboard:ai-thesis-collapsed",
    true, // default collapsed so a fresh dashboard fits on one screen
  );
  return (
    <section
      aria-label="AI thesis"
      className="border border-line-1 rounded-md bg-surface-1 px-4 py-3 flex flex-col gap-2"
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex items-center gap-2">
          <CollapseToggle
            collapsed={collapsed}
            onToggle={toggle}
            label="AI thesis"
          />
          <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
            AI Thesis · {instrument.symbol}
          </span>
        </div>
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          {CURVE_LABEL[thesis.curve_shape]}
        </span>
      </div>

      {collapsed ? null : (
        <>
          <div className="grid grid-cols-2 gap-4">
            {/* Left half: thesis prose */}
            <div>
              {hasThesis ? (
                <p className="text-sm text-ink-2 leading-relaxed">
                  {thesis.thesis}
                </p>
              ) : (
                <p className="text-sm text-ink-4 italic">
                  Thesis unavailable for this snapshot.
                </p>
              )}
            </div>

            {/* Right half: drivers stacked over watch */}
            <div className="flex flex-col gap-3">
              <div>
                <div className="font-mono text-[10px] text-ink-3 uppercase tracking-widest mb-1">
                  Key drivers
                </div>
                {thesis.drivers.length === 0 ? (
                  <span className="text-[11px] text-ink-4 font-mono">—</span>
                ) : (
                  <ul className="flex flex-col gap-0.5">
                    {thesis.drivers.map((d) => (
                      <li
                        key={d}
                        className="text-[12px] text-ink-2 leading-snug flex gap-1.5"
                      >
                        <span className="text-up shrink-0">+</span>
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <div className="font-mono text-[10px] text-ink-3 uppercase tracking-widest mb-1">
                  Watch
                </div>
                {thesis.watch.length === 0 ? (
                  <span className="text-[11px] text-ink-4 font-mono">—</span>
                ) : (
                  <ul className="flex flex-col gap-0.5">
                    {thesis.watch.map((w) => (
                      <li
                        key={w}
                        className="text-[12px] text-ink-2 leading-snug flex gap-1.5"
                      >
                        <span className="text-conf-medium shrink-0">◇</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {hasLists && (
            <SafetyEnvelopeNote envelope={thesis.safety} defaultOpen={false} />
          )}
        </>
      )}
    </section>
  );
}
