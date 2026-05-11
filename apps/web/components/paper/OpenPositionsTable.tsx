"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { closePaperTrade } from "../../lib/api";
import { queryKeys } from "../../lib/queries";
import { useChannel } from "../../lib/realtime";
import type { PriceTick, Trade } from "../../app/(app)/paper/types";
import { NG_TICK_VALUE_USD } from "../../app/(app)/paper/types";

interface Props {
  trades: Trade[];
}

function fmtDate(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function computeMtm(
  trade: Pick<Trade, "side" | "size_contracts" | "entry_price">,
  livePrice: number,
): number {
  const direction = trade.side === "long" ? 1 : -1;
  return (
    direction *
    (livePrice - trade.entry_price) *
    trade.size_contracts *
    NG_TICK_VALUE_USD
  );
}

export function OpenPositionsTable({ trades }: Props) {
  const { data: tick } = useChannel<PriceTick>("price.NG.front");
  const livePrice = tick?.price ?? null;
  const queryClient = useQueryClient();

  const closeMutation = useMutation<unknown, Error, string>({
    mutationFn: async (id: string) => closePaperTrade(id, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.paperTrades("open") });
      queryClient.invalidateQueries({
        queryKey: queryKeys.paperTrades("closed"),
      });
      queryClient.invalidateQueries({ queryKey: ["paper", "equity-curve"] });
    },
  });

  return (
    <div className="border border-line-1 bg-surface-1 flex flex-col">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-3">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Open Positions
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums ml-auto">
          live{" "}
          {livePrice !== null ? `$${livePrice.toFixed(3)}` : "—"}
        </span>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-line-1 text-ink-3 text-[10px] uppercase tracking-widest">
              <th className="text-left px-3 py-1.5">Opened</th>
              <th className="text-left px-3 py-1.5">Contract</th>
              <th className="text-left px-3 py-1.5">Side</th>
              <th className="text-right px-3 py-1.5">Size</th>
              <th className="text-right px-3 py-1.5">Entry</th>
              <th className="text-right px-3 py-1.5">Stop</th>
              <th className="text-right px-3 py-1.5">Take</th>
              <th className="text-right px-3 py-1.5">MTM PnL</th>
              <th className="text-center px-3 py-1.5">Action</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 && (
              <tr>
                <td colSpan={9} className="text-center text-ink-4 py-4">
                  No open positions.
                </td>
              </tr>
            )}
            {trades.map((t) => {
              const mtm =
                livePrice !== null ? computeMtm(t, livePrice) : null;
              const pnlClass =
                mtm === null
                  ? "text-ink-4"
                  : mtm > 0
                    ? "text-up"
                    : mtm < 0
                      ? "text-down"
                      : "text-flat";
              return (
                <tr
                  key={t.id}
                  className="border-b border-line-1 hover:bg-surface-2"
                  data-testid="open-trade-row"
                >
                  <td className="px-3 py-1.5 tabular-nums text-ink-3">
                    {fmtDate(t.opened_at)}
                  </td>
                  <td className="px-3 py-1.5 text-ink-2">
                    {t.contract_id ? t.contract_id.slice(0, 8) : "NG"}
                  </td>
                  <td
                    className={`px-3 py-1.5 ${
                      t.side === "long" ? "text-up" : "text-down"
                    }`}
                  >
                    {t.side}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-2">
                    {t.size_contracts.toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-2">
                    {t.entry_price.toFixed(3)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                    {t.stop_loss !== null ? t.stop_loss.toFixed(3) : "—"}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                    {t.take_profit !== null
                      ? t.take_profit.toFixed(3)
                      : "—"}
                  </td>
                  <td
                    className={`px-3 py-1.5 tabular-nums text-right ${pnlClass}`}
                    data-testid="mtm-pnl"
                  >
                    {mtm === null
                      ? "—"
                      : `${mtm >= 0 ? "+" : "-"}$${Math.abs(mtm).toFixed(0)}`}
                  </td>
                  <td className="px-3 py-1.5 text-center">
                    <button
                      type="button"
                      onClick={() => closeMutation.mutate(t.id)}
                      disabled={closeMutation.isPending}
                      className="font-mono text-[10px] uppercase tracking-widest text-accent disabled:text-ink-4"
                      data-testid="close-trade-btn"
                    >
                      Close
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
