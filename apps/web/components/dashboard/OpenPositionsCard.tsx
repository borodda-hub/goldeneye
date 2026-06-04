"use client";

import type { PriceTick, Trade, TradesResponse } from "@/app/(app)/paper/types";
import { NG_TICK_VALUE_USD } from "@/app/(app)/paper/types";
import { computeMtm } from "@/components/paper/OpenPositionsTable";
import { usePaperTrades } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const sign = v >= 0 ? "+" : "-";
  return `${sign}$${abs.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function fmtSize(n: number): string {
  return n % 1 === 0 ? n.toFixed(0) : n.toFixed(1);
}

export function OpenPositionsCard() {
  const { data } = usePaperTrades("open");
  const trades = ((data as TradesResponse | undefined)?.trades ??
    []) as Trade[];
  const { data: tick } = useChannel<PriceTick>("price.NG.front");
  const livePrice = tick?.price ?? null;

  return (
    <div
      className="border border-line-1 bg-surface-1 rounded-md flex flex-col"
      aria-label="Open positions"
    >
      <div className="flex items-baseline justify-between px-3 pt-2 pb-1.5 border-b border-line-1">
        <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          Positions
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {trades.length} open
        </span>
      </div>

      {trades.length === 0 ? (
        <div className="px-3 py-4 text-center text-[11px] font-mono text-ink-4">
          No open positions.
        </div>
      ) : (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-ink-4 text-[9px] uppercase tracking-widest">
              <th className="text-left px-3 py-1">Symbol</th>
              <th className="text-right px-3 py-1">Qty</th>
              <th className="text-right px-3 py-1">Entry</th>
              <th className="text-right px-3 py-1">Day P/L</th>
            </tr>
          </thead>
          <tbody>
            {trades.slice(0, 6).map((t) => {
              const mtm = livePrice !== null ? computeMtm(t, livePrice) : null;
              const tone =
                mtm === null
                  ? "text-ink-4"
                  : mtm > 0
                    ? "text-up"
                    : mtm < 0
                      ? "text-down"
                      : "text-flat";
              const arrow =
                mtm === null || mtm === 0 ? "·" : mtm > 0 ? "▲" : "▼";
              return (
                <tr
                  key={t.id}
                  className="border-t border-line-1/60"
                  data-testid="dash-open-row"
                >
                  <td className="px-3 py-1.5">
                    <span className="text-ink-1">
                      {t.contract_id ? t.contract_id.slice(0, 6) : "NG"}
                    </span>
                    <span
                      className={`ml-1 text-[9px] uppercase ${
                        t.side === "long" ? "text-up" : "text-down"
                      }`}
                    >
                      {t.side}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-ink-2">
                    {fmtSize(t.size_contracts)}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-ink-2">
                    {t.entry_price.toFixed(3)}
                  </td>
                  <td
                    className={`px-3 py-1.5 text-right tabular-nums ${tone}`}
                    data-testid="dash-mtm"
                  >
                    {arrow} {mtm === null ? "—" : fmtUsd(mtm)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <div className="px-3 py-1 border-t border-line-1 text-[9px] font-mono text-ink-4 uppercase tracking-widest text-right">
        tick value ${NG_TICK_VALUE_USD.toLocaleString()}
      </div>
    </div>
  );
}
