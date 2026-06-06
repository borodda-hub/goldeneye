"use client";

/**
 * Keeps a signed-in user's `goldeneye:*` workspace state (theme, chart
 * drawings/indicators, layout, active instrument, onboarding) in sync with
 * their account, so it follows them across devices — the "come back to what
 * you did" payoff. No-op when signed out or when accounts are disabled.
 *
 * Mounted only under <ClerkProvider> (gated on `clerkEnabled` by the caller),
 * so the Clerk hook is always safe to call here.
 */

import { getMySettings, putMySettings } from "@/lib/api";
import { applySettings, collectSettings } from "@/lib/userSettings";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useRef } from "react";

const POLL_MS = 4000; // how often we check local state for changes to push
const DEBOUNCE_MS = 1200; // settle window before a push

export function ProfileSync() {
  const { isLoaded, isSignedIn } = useAuth();
  const lastSynced = useRef<string>("");
  const hydrated = useRef(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    let pushTimer: ReturnType<typeof setTimeout> | undefined;

    // 1. Hydrate from the server once per sign-in (server wins).
    (async () => {
      try {
        const { settings } = await getMySettings();
        if (cancelled) return;
        if (settings && Object.keys(settings).length > 0) {
          applySettings(settings);
          lastSynced.current = JSON.stringify(collectSettings());
        } else {
          // First sign-in on this account: seed the server from local state.
          const local = collectSettings();
          lastSynced.current = JSON.stringify(local);
          if (Object.keys(local).length > 0) await putMySettings(local);
        }
        hydrated.current = true;
      } catch {
        // offline / accounts-off — stay on localStorage, sync later.
      }
    })();

    // 2. Push local changes up (a poll catches same-tab edits the `storage`
    //    event misses; debounced so rapid edits collapse into one PUT).
    const maybePush = () => {
      if (!hydrated.current || cancelled) return;
      const snap = JSON.stringify(collectSettings());
      if (snap === lastSynced.current) return;
      lastSynced.current = snap;
      clearTimeout(pushTimer);
      pushTimer = setTimeout(() => {
        putMySettings(collectSettings()).catch(() => {});
      }, DEBOUNCE_MS);
    };
    const poll = setInterval(maybePush, POLL_MS);

    return () => {
      cancelled = true;
      clearTimeout(pushTimer);
      clearInterval(poll);
    };
  }, [isLoaded, isSignedIn]);

  return null;
}
