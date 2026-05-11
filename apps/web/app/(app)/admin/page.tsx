import { getAlerts, getDataHealth } from "../../../lib/api";
import { AdminShell } from "./AdminShell";
import type { AlertsResponse, DataHealth } from "./types";

const ENV_VAR_NAMES = [
  "NEXT_PUBLIC_API_BASE",
  "DATABASE_URL",
  "REDIS_URL",
  "LLM_MODE",
  "LLM_MODEL_FAST",
  "LLM_MODEL_SMART",
];

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

  const envFlags: Record<string, boolean> = {};
  for (const name of ENV_VAR_NAMES) {
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
