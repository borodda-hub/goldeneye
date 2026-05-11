"use client";

import { useChannel } from "@/lib/realtime";
import { LiveDot } from "@/components/LiveDot";

interface TickData {
  ts: string;
  price: number;
  size: number;
}

function formatTickTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    const h = d.getUTCHours().toString().padStart(2, "0");
    const m = d.getUTCMinutes().toString().padStart(2, "0");
    const s = d.getUTCSeconds().toString().padStart(2, "0");
    return `${h}:${m}:${s} ET`;
  } catch {
    return isoString;
  }
}

export function DashboardLiveBar() {
  const { data: tick, status } = useChannel<TickData>("price.NG.front");

  const statusLabel =
    status === "connected"
      ? "connected"
      : status === "connecting"
        ? "connecting…"
        : "disconnected";

  return (
    <div className="flex items-center gap-3 text-xs font-mono text-ink-3 pt-2 border-t border-line-1">
      <div className="flex items-center gap-1.5">
        <LiveDot connected={status === "connected"} />
        <span>{statusLabel}</span>
      </div>

      {tick && (
        <span>
          NGF26 · {tick.price.toFixed(3)} · {formatTickTime(tick.ts)}
        </span>
      )}

      {status === "connected" && (
        <span className="ml-auto text-accent">LIVE</span>
      )}
    </div>
  );
}
