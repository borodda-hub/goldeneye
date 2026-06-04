import { readActiveSymbolFromSearchParams } from "@/lib/activeInstrument";
import { getChartBars, getChartCurve } from "@/lib/api";
import { ChartShell } from "./ChartShell";
import type { ChartBarsResponse, CurvePoint } from "./types";

interface CurveResponse {
  symbol: string;
  as_of: string;
  curve: Array<{
    contract_code: string;
    expiry: string;
    mid_price?: number;
    mid?: number;
  }>;
}

const FRONT_MONTH_FALLBACK_BY_SYMBOL: Record<string, string> = {
  NG: "NGM26",
  CL: "CLN26",
};

interface Props {
  searchParams?: Record<string, string | string[] | undefined>;
}

export default async function ChartPage({ searchParams }: Props) {
  const symbol = readActiveSymbolFromSearchParams(searchParams);
  const today = new Date().toISOString().split("T")[0];
  const twoYearsAgo = new Date(Date.now() - 730 * 86400_000)
    .toISOString()
    .split("T")[0];

  let initialBars: ChartBarsResponse | null = null;
  let initialCurve: CurvePoint[] | null = null;
  let contractCode = FRONT_MONTH_FALLBACK_BY_SYMBOL[symbol] ?? "NGM26";

  // Step 1: resolve the current front-month via the curve endpoint. The
  // backend already sorts by expiry, so curve[0] IS the front month.
  try {
    const curveResp = (await getChartCurve(symbol, today)) as CurveResponse;
    const items = curveResp?.curve ?? [];
    if (items.length > 0) {
      contractCode = items[0].contract_code;
      initialCurve = items.map((item) => ({
        contract_code: item.contract_code,
        expiry: item.expiry,
        mid: item.mid_price ?? item.mid ?? 0,
      }));
    }
  } catch {
    // Curve unavailable — fall back to the hardcoded contract.
  }

  // Step 2: fetch bars for whichever contract we resolved.
  try {
    initialBars = (await getChartBars({
      contract_code: contractCode,
      resolution: "1d",
      from: twoYearsAgo,
      to: today,
    })) as ChartBarsResponse;
  } catch {
    // Backend offline or contract still missing — shell will retry client-side.
  }

  return (
    <ChartShell
      initialBars={initialBars}
      initialCurve={initialCurve}
      contractCode={contractCode}
      initialSymbol={symbol}
    />
  );
}
