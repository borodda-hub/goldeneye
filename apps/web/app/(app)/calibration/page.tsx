import { readActiveSymbolFromSearchParams } from "../../../lib/activeInstrument";
import { getCalibration } from "../../../lib/api";
import type { CalibrationResponse } from "../../../lib/api";
import { CalibrationShell } from "./CalibrationShell";

interface Props {
  searchParams?: Record<string, string | string[] | undefined>;
}

export default async function CalibrationPage({ searchParams }: Props) {
  const symbol = readActiveSymbolFromSearchParams(searchParams);
  let initial: CalibrationResponse | null = null;
  try {
    initial = await getCalibration(symbol, 5);
  } catch {
    // Server-side prefetch failed; client will refetch via TanStack Query.
  }
  return (
    <div className="flex flex-col h-full">
      <CalibrationShell initialData={initial} initialSymbol={symbol} />
    </div>
  );
}
