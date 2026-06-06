"use client";

import { CircleDollarSign, Layers, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  EquityPoint,
  PriceTick,
  Trade,
} from "../../app/(app)/paper/types";
import { useChannel } from "../../lib/realtime";
import { CountUp } from "../CountUp";
import { computeMtm } from "./OpenPositionsTable";

const STARTING_EQUITY = 100_000;

interface Props {
  open: Trade[];
  closed: Trade[];
  equity: EquityPoint[];
}

function Tile({
  label,
  icon: Icon,
  children,
  sub,
}: {
  label: string;
  icon: LucideIcon;
  children: React.ReactNode;
  sub?: React.ReactNode;
}) {
  return (
    <div className="card-interactive flex-1 rounded-sm border border-line-1 bg-surface-1 px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-ink-3">
          {label}
        </span>
        <Icon
          size={13}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
      </div>
      <div className="mt-1.5 font-mono text-lg tabular-nums text-ink-1">
        {children}
      </div>
      {sub && (
        <div className="mt-0.5 font-mono text-[10px] tabular-nums text-ink-4">
          {sub}
        </div>
      )}
    </div>
  );
}

/** Live P&L summary across the top of Paper Trading: net liquidity, open MTM,
 *  realized P&L and open-position count, each rolling into place on update. */
export function PaperStatStrip({ open, closed, equity }: Props) {
  const { data: tick } = useChannel<PriceTick>("price.NG.front");
  const livePrice = tick?.price ?? null;

  const lastEquity =
    equity.length > 0 ? equity[equity.length - 1].equity : STARTING_EQUITY;
  const openMtm =
    livePrice !== null
      ? open.reduce((sum, t) => sum + computeMtm(t, livePrice), 0)
      : 0;
  const realized = closed.reduce((sum, t) => sum + (t.outcome_pnl ?? 0), 0);
  const retPct = ((lastEquity - STARTING_EQUITY) / STARTING_EQUITY) * 100;

  const pnlColor = (v: number) =>
    v > 0 ? "text-up" : v < 0 ? "text-down" : "text-flat";

  return (
    <div className="flex gap-3">
      <Tile
        label="Net Liquidity"
        icon={Wallet}
        sub={
          <span className={pnlColor(retPct)}>
            {retPct >= 0 ? "+" : ""}
            {retPct.toFixed(2)}% vs start
          </span>
        }
      >
        <CountUp value={lastEquity} prefix="$" precision={0} />
      </Tile>

      <Tile
        label="Open P&L · MTM"
        icon={TrendingUp}
        sub={`${open.length} position${open.length === 1 ? "" : "s"} · ${
          livePrice !== null ? "live" : "no tick"
        }`}
      >
        <CountUp
          value={openMtm}
          prefix="$"
          precision={0}
          signed
          className={pnlColor(openMtm)}
        />
      </Tile>

      <Tile
        label="Realized P&L"
        icon={CircleDollarSign}
        sub={`${closed.length} closed`}
      >
        <CountUp
          value={realized}
          prefix="$"
          precision={0}
          signed
          className={pnlColor(realized)}
        />
      </Tile>

      <Tile label="Open Positions" icon={Layers} sub="mark-to-market">
        <CountUp value={open.length} precision={0} />
      </Tile>
    </div>
  );
}
