import { beforeEach, describe, expect, it, vi } from "vitest";
import { applySettings, collectSettings } from "../userSettings";

describe("userSettings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("collects only goldeneye:* keys", () => {
    localStorage.setItem("goldeneye:theme", "ember");
    localStorage.setItem("goldeneye:chart:drawings:NG", "[]");
    localStorage.setItem("unrelated", "nope");

    const snap = collectSettings();

    expect(snap).toEqual({
      "goldeneye:theme": "ember",
      "goldeneye:chart:drawings:NG": "[]",
    });
    expect(snap).not.toHaveProperty("unrelated");
  });

  it("round-trips collect -> apply", () => {
    const server = {
      "goldeneye:theme": "abyss",
      "goldeneye:active-instrument": "HO",
    };
    applySettings(server);
    expect(collectSettings()).toEqual(server);
  });

  it("never writes foreign keys", () => {
    applySettings({ "evil:key": "x", "goldeneye:theme": "nord" });
    expect(localStorage.getItem("evil:key")).toBeNull();
    expect(localStorage.getItem("goldeneye:theme")).toBe("nord");
  });

  it("dispatches a storage event for changed keys so providers re-apply", () => {
    localStorage.setItem("goldeneye:theme", "slate");
    const events: StorageEvent[] = [];
    const handler = (e: Event) => events.push(e as StorageEvent);
    window.addEventListener("storage", handler);

    applySettings({ "goldeneye:theme": "ember" });

    window.removeEventListener("storage", handler);
    expect(events).toHaveLength(1);
    expect(events[0].key).toBe("goldeneye:theme");
    expect(events[0].newValue).toBe("ember");
  });

  it("does not dispatch when the value is unchanged", () => {
    localStorage.setItem("goldeneye:theme", "ember");
    const handler = vi.fn();
    window.addEventListener("storage", handler);

    applySettings({ "goldeneye:theme": "ember" });

    window.removeEventListener("storage", handler);
    expect(handler).not.toHaveBeenCalled();
  });
});
