import { getDashboardSummary } from "@/lib/api";
import { DashboardShell } from "./DashboardShell";
import type { DashboardSummary } from "./types";

export default async function DashboardPage() {
  let initialData: DashboardSummary | null = null;
  try {
    initialData = (await getDashboardSummary("NG")) as DashboardSummary;
  } catch {
    // Backend offline — shell will retry client-side
  }
  return <DashboardShell initialData={initialData} />;
}
