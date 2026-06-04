"use client";

import { useEffect, useState } from "react";

/**
 * Tri-state collapse with localStorage persistence. SSR-safe — first render
 * uses `defaultCollapsed`; the persisted value loads after mount.
 */
export function useCollapsed(
  storageKey: string,
  defaultCollapsed = false,
): { collapsed: boolean; toggle: () => void; setCollapsed: (v: boolean) => void } {
  const [collapsed, setCollapsedState] = useState(defaultCollapsed);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw === "1") setCollapsedState(true);
      else if (raw === "0") setCollapsedState(false);
    } catch {
      // ignore
    }
  }, [storageKey]);

  const setCollapsed = (v: boolean) => {
    setCollapsedState(v);
    try {
      localStorage.setItem(storageKey, v ? "1" : "0");
    } catch {
      // ignore
    }
  };

  return {
    collapsed,
    toggle: () => setCollapsed(!collapsed),
    setCollapsed,
  };
}
