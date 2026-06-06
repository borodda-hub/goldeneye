"use client";

import { Wallet } from "lucide-react";
import { PageHeader } from "../../../components/PageHeader";
import { ClosedTradesTable } from "../../../components/paper/ClosedTradesTable";
import { EquityCurveChart } from "../../../components/paper/EquityCurveChart";
import { NewTradeForm } from "../../../components/paper/NewTradeForm";
import { OpenPositionsTable } from "../../../components/paper/OpenPositionsTable";
import { PaperStatStrip } from "../../../components/paper/PaperStatStrip";
import { usePaperEquityCurve, usePaperTrades } from "../../../lib/queries";
import { useActiveInstrument } from "../../../lib/useActiveInstrument";
import type { JournalEntry } from "../journal/types";
import type {
  EquityCurveResponse,
  EquityPoint,
  Trade,
  TradesResponse,
} from "./types";

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
    <div className="stagger flex flex-col gap-4" data-tour="paper-shell">
      <PageHeader
        icon={Wallet}
        title="Paper Trading"
        subtitle="Simulated execution · mark-to-market"
      />

      <PaperStatStrip open={openTrades} closed={closedTrades} equity={equity} />

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
