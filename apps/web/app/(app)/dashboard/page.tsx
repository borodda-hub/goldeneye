import { getDashboardSummary } from "@/lib/api";
import { readActiveSymbolFromSearchParams } from "@/lib/useActiveInstrument";
import { DashboardShell } from "./DashboardShell";
import type { DashboardSummary } from "./types";

interface Props {
  searchParams?: Record<string, string | string[] | undefined>;
}

export default async function DashboardPage({ searchParams }: Props) {
  const symbol = readActiveSymbolFromSearchParams(searchParams);
  let initialData: DashboardSummary | null = null;
  try {
    initialData = (await getDashboardSummary(symbol)) as DashboardSummary;
  } catch {
    // Backend offline — shell will retry client-side
  }
  return <DashboardShell initialData={initialData} initialSymbol={symbol} />;
}
