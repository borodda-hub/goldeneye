import { getCalibration } from "../../../lib/api";
import type { CalibrationResponse } from "../../../lib/api";
import { CalibrationShell } from "./CalibrationShell";

export default async function CalibrationPage() {
  let initial: CalibrationResponse | null = null;
  try {
    initial = await getCalibration("NG", 5);
  } catch {
    // Server-side prefetch failed; client will refetch via TanStack Query.
  }
  return (
    <div className="flex flex-col h-full">
      <CalibrationShell initialData={initial} />
    </div>
  );
}
