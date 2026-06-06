/**
 * Profile settings sync — the bridge between the browser's `goldeneye:*`
 * localStorage state (theme, chart drawings, indicators, layout, active
 * instrument, onboarding) and a signed-in user's account.
 *
 * `collectSettings()` snapshots that state into a flat string map; the server
 * stores it as one JSON blob (`/v1/me/settings`). `applySettings()` writes a
 * server snapshot back into localStorage and dispatches synthetic `storage`
 * events so live providers (ThemeProvider, useChartColor, useActiveInstrument)
 * re-apply without a reload. Keys outside the `goldeneye:` namespace are never
 * touched.
 */

const PREFIX = "goldeneye:";

/** Snapshot every `goldeneye:*` localStorage entry into a flat string map. */
export function collectSettings(): Record<string, string> {
  const out: Record<string, string> = {};
  if (typeof window === "undefined") return out;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(PREFIX)) {
        const value = localStorage.getItem(key);
        if (value !== null) out[key] = value;
      }
    }
  } catch {
    // localStorage unavailable — return whatever we gathered.
  }
  return out;
}

/** Write a server snapshot back to localStorage, notifying live listeners of
 *  any key that actually changed so the UI updates without a reload. */
export function applySettings(settings: Record<string, string>): void {
  if (typeof window === "undefined") return;
  for (const [key, value] of Object.entries(settings)) {
    if (!key.startsWith(PREFIX)) continue; // never touch foreign keys
    let oldValue: string | null = null;
    try {
      oldValue = localStorage.getItem(key);
      if (oldValue === value) continue;
      localStorage.setItem(key, value);
    } catch {
      continue;
    }
    // Same-tab writes don't fire `storage`; synthesize it so providers that
    // listen (theme, chart color, active instrument) re-hydrate live.
    window.dispatchEvent(
      new StorageEvent("storage", { key, oldValue, newValue: value }),
    );
  }
}
