"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { WalkthroughOverlay } from "./WalkthroughOverlay";
import { DASHBOARD_TOUR, type WalkthroughStep } from "./steps";

const STORAGE_KEY = "goldeneye:walkthrough-completed";

interface ContextShape {
  open: boolean;
  start: () => void;
  stop: () => void;
}

const Ctx = createContext<ContextShape>({
  open: false,
  start: () => undefined,
  stop: () => undefined,
});

export function useWalkthrough(): ContextShape {
  return useContext(Ctx);
}

export function WalkthroughProvider({
  children,
}: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  const steps: WalkthroughStep[] = DASHBOARD_TOUR;

  const start = useCallback(() => {
    // If the first step requires a route, push there first.
    const first = steps[0];
    if (first.routeRequired && pathname !== first.routeRequired) {
      router.push(first.routeRequired);
    }
    setStepIndex(0);
    setOpen(true);
  }, [pathname, router, steps]);

  const stop = useCallback(() => {
    setOpen(false);
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignore
    }
  }, []);

  const next = useCallback(() => {
    setStepIndex((i) => {
      if (i + 1 >= steps.length) {
        // last step → close after the user clicks "next" on the farewell
        return i;
      }
      return i + 1;
    });
  }, [steps.length]);

  const prev = useCallback(() => {
    setStepIndex((i) => Math.max(0, i - 1));
  }, []);

  // Push the router whenever the active step demands a different route.
  // Runs on every stepIndex change while the tour is open.
  // biome-ignore lint/correctness/useExhaustiveDependencies: pathname is intentionally omitted — including it would re-run the effect on every navigation; the equality check inside short-circuits on the next render instead. `steps` is the module constant DASHBOARD_TOUR and is stable.
  useEffect(() => {
    if (!open) return;
    const step = steps[stepIndex];
    if (!step?.routeRequired) return;
    if (pathname === step.routeRequired) return;
    router.push(step.routeRequired);
    // pathname is intentionally NOT in deps — the next render with the
    // new pathname will short-circuit on the equality check above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, stepIndex, router]);

  // Auto-trigger on first visit ever (any page).  Only fires once because
  // start() persists the completed flag on stop().
  useEffect(() => {
    try {
      const seen = localStorage.getItem(STORAGE_KEY);
      if (seen) return;
    } catch {
      return;
    }
    // Defer 800 ms so the dashboard finishes its first paint before the
    // spotlight tries to locate targets.
    const tid = setTimeout(() => {
      if (pathname === "/dashboard") {
        setStepIndex(0);
        setOpen(true);
      }
    }, 800);
    return () => clearTimeout(tid);
    // intentionally only on mount + when pathname becomes /dashboard
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <Ctx.Provider value={{ open, start, stop }}>
      {children}
      {open ? (
        <WalkthroughOverlay
          steps={steps}
          stepIndex={stepIndex}
          onNext={next}
          onPrev={prev}
          onClose={stop}
        />
      ) : null}
    </Ctx.Provider>
  );
}
