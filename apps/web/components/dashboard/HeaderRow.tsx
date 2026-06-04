"use client";

import type {
  FrontMonth,
  Instrument,
  VolRegime,
} from "@/app/(app)/dashboard/types";
import { LiveDot } from "@/components/LiveDot";
import { NumberCell } from "@/components/NumberCell";
import { SignalQualityChip } from "@/components/dashboard/SignalQualityChip";
import type { ConnectionStatus } from "@/lib/realtime";
import { flashBgClass, usePriceFlash } from "@/lib/usePriceFlash";

interface Props {
  instrument: Instrument;
  frontMonth: FrontMonth;
  volRegime: VolRegime;
  livePrice?: number;
  wsStatus: ConnectionStatus;
  feedMode?: "live" | "delayed";
}

const REGIME_STYLES: Record<VolRegime, string> = {
  compressed: "bg-surface-2 text-ink-3",
  normal: "bg-surface-2 text-flat",
  elevated: "bg-down-soft text-down",
  crisis: "bg-down-soft text-down font-semibold",
} as const;

function VolRegimeChip({ regime }: { regime: VolRegime }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-mono ${REGIME_STYLES[regime]}`}
    >
      VOL: {regime}
    </span>
  );
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    const h = d.getUTCHours().toString().padStart(2, "0");
    const m = d.getUTCMinutes().toString().padStart(2, "0");
    return `${h}:${m} ET`;
  } catch {
    return isoString;
  }
}

export function HeaderRow({
  instrument,
  frontMonth,
  volRegime,
  livePrice,
  wsStatus,
  feedMode = "live",
}: Props) {
  const displayPrice = livePrice ?? frontMonth.last_price;
  const flash = usePriceFlash(displayPrice);
  const changeAbs = frontMonth.change_abs;
  const changePct = frontMonth.change_pct;
  const hasChange = changeAbs !== null && changePct !== null;
  const isUp = hasChange && (changeAbs as number) > 0;
  const isDown = hasChange && (changeAbs as number) < 0;
  const changeColor = isUp ? "text-up" : isDown ? "text-down" : "text-flat";
  const changeSign = isUp ? "▲" : isDown ? "▼" : "";
  const pctSign = hasChange && (changePct as number) > 0 ? "+" : "";

  return (
    <div className="flex items-center justify-between gap-6 pb-3 border-b border-line-1">
      {/* Left: identifiers */}
      <div className="flex items-center gap-2 text-xs">
        <span className="font-mono text-sm font-semibold text-ink-1">
          {instrument.symbol}
        </span>
        <span className="text-ink-4">·</span>
        <span className="font-mono text-xs text-ink-3">
          {frontMonth.contract_code}
        </span>
        <span className="text-ink-4">·</span>
        <span className="text-xs text-ink-3">{instrument.name}</span>
      </div>

      {/* Center: price */}
      <div
        className={`flex items-center gap-3 rounded-md px-2 -mx-2 py-0.5 transition-colors duration-500 ${flashBgClass(flash)}`}
      >
        <NumberCell value={displayPrice} precision={3} />
        {hasChange ? (
          <>
            <span className={`font-mono text-sm tabular-nums ${changeColor}`}>
              {changeSign} {Math.abs(changeAbs as number).toFixed(3)}
            </span>
            <span className={`font-mono text-sm tabular-nums ${changeColor}`}>
              ({pctSign}
              {((changePct as number) * 100).toFixed(2)}%)
            </span>
          </>
        ) : (
          <span className="font-mono text-sm tabular-nums text-ink-4">—</span>
        )}
      </div>

      {/* Right: signal quality, vol regime, status, time */}
      <div className="flex items-center gap-3">
        <SignalQualityChip symbol={instrument.symbol} />
        <VolRegimeChip regime={volRegime} />
        <LiveDot connected={wsStatus === "connected"} mode={feedMode} />
        <span className="font-mono text-xs text-ink-3">
          {formatTime(frontMonth.as_of)}
        </span>
      </div>
    </div>
  );
}
