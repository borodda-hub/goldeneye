import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  ONBOARDING_STEPS,
  markSeen,
  markStep,
  reset,
  setDismissed,
  useOnboarding,
} from "../onboarding";

beforeEach(() => {
  localStorage.clear();
});

describe("onboarding state", () => {
  it("defaults to nothing-seen / nothing-done (SSR-safe)", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.seen).toBe(false);
    expect(result.current.completedCount).toBe(0);
    expect(result.current.steps.every((s) => !s.done)).toBe(true);
  });

  it("markStep sets the flag, bumps completedCount, and re-renders the hook", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => markStep("thesis"));
    expect(result.current.completedCount).toBe(1);
    expect(result.current.steps.find((s) => s.id === "thesis")?.done).toBe(
      true,
    );
    expect(localStorage.getItem("goldeneye:onboarding:step:thesis")).toBe("1");
  });

  it("markStep is idempotent (no duplicate counting)", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => {
      markStep("scenario");
      markStep("scenario");
    });
    expect(result.current.completedCount).toBe(1);
  });

  it("markSeen and setDismissed flow through the hook", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => markSeen());
    expect(result.current.seen).toBe(true);
    act(() => setDismissed(true));
    expect(result.current.dismissed).toBe(true);
  });

  it("reset clears all flags", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => {
      markSeen();
      for (const s of ONBOARDING_STEPS) markStep(s.id);
    });
    expect(result.current.completedCount).toBe(ONBOARDING_STEPS.length);
    act(() => reset());
    expect(result.current.seen).toBe(false);
    expect(result.current.completedCount).toBe(0);
  });
});
