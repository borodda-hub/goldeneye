import { getAlerts, getDataHealth } from "../../../lib/api";
import { AdminShell } from "./AdminShell";
import type { AlertsResponse, DataHealth } from "./types";

// NEXT_PUBLIC_API_BASE is the only env var the web bundle owns — the rest
// (DATABASE_URL, LLM_MODE, ADAPTER_*) live in the FastAPI process's
// environment and arrive in the data-health response's `env_flags` field.
const WEB_ONLY_ENV_VARS = ["NEXT_PUBLIC_API_BASE"] as const;

export default async function AdminPage() {
  let initialHealth: DataHealth | null = null;
  let initialAlerts: AlertsResponse | null = null;

  try {
    initialHealth = (await getDataHealth()) as DataHealth;
  } catch {
    // Server prefetch failed; client will retry
  }
  try {
    initialAlerts = (await getAlerts({ unread: false })) as AlertsResponse;
  } catch {
    // Server prefetch failed; client will retry
  }

  // Compose env flags from both sources:
  //   - the API for server-side vars (DATABASE_URL, LLM_*, ADAPTER_*, etc.)
  //   - process.env (Next.js) for bundle-time NEXT_PUBLIC_* vars.
  const envFlags: Record<string, boolean> = {
    ...(initialHealth?.env_flags ?? {}),
  };
  for (const name of WEB_ONLY_ENV_VARS) {
    envFlags[name] = Boolean(process.env[name]);
  }

  const gitSha = process.env.NEXT_PUBLIC_GIT_SHA ?? process.env.VERCEL_GIT_COMMIT_SHA;
  const buildTime = process.env.NEXT_PUBLIC_BUILD_TIME;

  return (
    <div className="flex flex-col h-full">
      <AdminShell
        initialHealth={initialHealth}
        initialAlerts={initialAlerts}
        envFlags={envFlags}
        gitSha={gitSha?.slice(0, 7)}
        buildTime={buildTime}
      />
    </div>
  );
}
