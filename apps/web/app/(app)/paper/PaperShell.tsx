"use client";

import {
  usePaperEquityCurve,
  usePaperTrades,
} from "../../../lib/queries";
import { useActiveInstrument } from "../../../lib/useActiveInstrument";
import { EquityCurveChart } from "../../../components/paper/EquityCurveChart";
import { OpenPositionsTable } from "../../../components/paper/OpenPositionsTable";
import { ClosedTradesTable } from "../../../components/paper/ClosedTradesTable";
import { NewTradeForm } from "../../../components/paper/NewTradeForm";
import type {
  EquityCurveResponse,
  EquityPoint,
  Trade,
  TradesResponse,
} from "./types";
import type { JournalEntry } from "../journal/types";

function isoDaysAgo(days: number): string {
  const d = new Date(Date.now() - days * 86_400_000);
  return d.toISOString().slice(0, 10);
}

interface Props {
  initialOpen: Trade[];
  initialClosed: Trade[];
  initialEquity: EquityPoint[];
  journalEntries: JournalEntry[];
}

export function PaperShell({
  initialOpen,
  initialClosed,
  initialEquity,
  journalEntries,
}: Props) {
  const since = isoDaysAgo(90);
  const { activeSymbol } = useActiveInstrument();

  const openQuery = usePaperTrades("open", activeSymbol);
  const closedQuery = usePaperTrades("closed", activeSymbol);
  const equityQuery = usePaperEquityCurve(since);

  const openTrades =
    (openQuery.data as TradesResponse | undefined)?.trades ?? initialOpen;
  const closedTrades =
    (closedQuery.data as TradesResponse | undefined)?.trades ?? initialClosed;
  const equity =
    (equityQuery.data as EquityCurveResponse | undefined)?.series ??
    initialEquity;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-ink-1">Paper Trading</h1>
        <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
          Simulated execution · mark-to-market
        </span>
      </div>

      <section className="h-48">
        <EquityCurveChart series={equity} />
      </section>

      <section className="flex gap-4">
        <div className="flex-1 min-w-0">
          <OpenPositionsTable trades={openTrades} />
        </div>
        <div className="w-96 shrink-0">
          <NewTradeForm journalEntries={journalEntries} />
        </div>
      </section>

      <section>
        <ClosedTradesTable trades={closedTrades} />
      </section>
    </div>
  );
}
