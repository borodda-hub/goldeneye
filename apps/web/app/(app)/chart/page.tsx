import { getChartBars, getChartCurve } from "@/lib/api";
import { ChartShell } from "./ChartShell";
import type { ChartBarsResponse, CurvePoint } from "./types";

export default async function ChartPage() {
  const today = new Date().toISOString().split("T")[0];
  const twoYearsAgo = new Date(Date.now() - 730 * 86400_000)
    .toISOString()
    .split("T")[0];

  let initialBars: ChartBarsResponse | null = null;
  let initialCurve: CurvePoint[] | null = null;

  try {
    initialBars = (await getChartBars({
      contract_code: "NGF26",
      resolution: "1d",
      from: twoYearsAgo,
      to: today,
    })) as ChartBarsResponse;
    initialCurve = (await getChartCurve("NG", today)) as CurvePoint[];
  } catch {
    // Backend offline
  }

  return <ChartShell initialBars={initialBars} initialCurve={initialCurve} />;
}
