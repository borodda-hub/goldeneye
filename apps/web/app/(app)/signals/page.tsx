import { getCurrentSignal } from "../../../lib/api";
import { SignalsShell } from "./SignalsShell";
import type { CurrentSignal } from "./types";

export default async function SignalsPage() {
  let initialSignal: CurrentSignal | null = null;
  try {
    initialSignal = (await getCurrentSignal("NG")) as CurrentSignal;
  } catch {
    // Server-side prefetch failed; client will retry via TanStack Query
  }

  return (
    <div className="flex flex-col h-full">
      <SignalsShell initialSignal={initialSignal} />
    </div>
  );
}
