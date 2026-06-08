"use client";

import {
  Segmented,
  type SegmentedOption,
} from "@/components/signals/Segmented";

export type SignalView = "both" | "range" | "direction";
export type VolEstimator = "ewma" | "har_log";

/**
 * Phase 30d — view + estimator selectors for Signal Lab.
 *
 * The user picks a *view*, never a "which model is right" toggle: direction and
 * range answer different questions and are not co-equal. Direction has no proven
 * out-of-sample edge (Phase 26 / confirmed real-OOS); the volatility range does
 * (Phase 30). Each surface still carries its own live calibration readout below,
 * so you can choose a view but can't escape its track record.
 */

const VIEW_OPTIONS: ReadonlyArray<SegmentedOption<SignalView>> = [
  {
    value: "both",
    label: "Both",
    title:
      "Direction (a view, no proven edge) above the calibrated volatility range.",
  },
  {
    value: "range",
    label: "Range",
    title: "The calibrated edge: the walk-forward volatility band only.",
  },
  {
    value: "direction",
    label: "Direction",
    title:
      "The ensemble's directional view — no proven out-of-sample edge (read as a view).",
  },
];

const ESTIMATOR_OPTIONS: ReadonlyArray<SegmentedOption<VolEstimator>> = [
  {
    value: "har_log",
    label: "log-HAR",
    title:
      "Log-HAR realized-variance model (default). Beat EWMA on real out-of-sample point accuracy across six commodities.",
  },
  {
    value: "ewma",
    label: "EWMA",
    title:
      "Exponentially-weighted vol — the original Phase 30a band. Cheap single pass; the explicit opt-out from the log-HAR default.",
  },
];

export function SignalViewControls({
  view,
  onViewChange,
  estimator,
  onEstimatorChange,
}: {
  view: SignalView;
  onViewChange: (v: SignalView) => void;
  estimator: VolEstimator;
  onEstimatorChange: (e: VolEstimator) => void;
}) {
  const showEstimator = view !== "direction";

  return (
    <div className="flex items-center gap-x-6 gap-y-2 flex-wrap">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
          View
        </span>
        <Segmented
          options={VIEW_OPTIONS}
          value={view}
          onChange={onViewChange}
          label="Signal Lab view"
        />
      </div>

      {showEstimator && (
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Vol estimator
          </span>
          <Segmented
            options={ESTIMATOR_OPTIONS}
            value={estimator}
            onChange={onEstimatorChange}
            label="Volatility estimator"
          />
        </div>
      )}
    </div>
  );
}
