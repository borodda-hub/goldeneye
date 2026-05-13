import { getCurrentSignal } from "../../../lib/api";
import { readActiveSymbolFromSearchParams } from "../../../lib/useActiveInstrument";
import { SignalsShell } from "./SignalsShell";
import type { CurrentSignal } from "./types";

interface Props {
  searchParams?: Record<string, string | string[] | undefined>;
}

export default async function SignalsPage({ searchParams }: Props) {
  const symbol = readActiveSymbolFromSearchParams(searchParams);
  let initialSignal: CurrentSignal | null = null;
  try {
    initialSignal = (await getCurrentSignal(symbol)) as CurrentSignal;
  } catch {
    // Server-side prefetch failed; client will retry via TanStack Query
  }

  return (
    <div className="flex flex-col h-full">
      <SignalsShell initialSignal={initialSignal} initialSymbol={symbol} />
    </div>
  );
}
