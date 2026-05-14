import { describe, expect, it } from "vitest";
import {
  DEFAULTS,
  MA_TYPES,
  isValidPeriod,
  newSpec,
  specToLabel,
  specToQueryFragment,
  specsToQueryParam,
  storageKey,
} from "../indicatorRegistry";

describe("indicatorRegistry", () => {
  it("has defaults for every MA type", () => {
    for (const t of MA_TYPES) {
      expect(DEFAULTS[t]).toBeDefined();
      expect(DEFAULTS[t].period).toBeGreaterThanOrEqual(2);
      expect(DEFAULTS[t].color).toMatch(/^#/);
    }
  });

  it("specToLabel formats as TYPE(period)", () => {
    const spec = newSpec("ema", { period: 21 });
    expect(specToLabel(spec)).toBe("EMA(21)");
  });

  it("specToQueryFragment omits :source when default", () => {
    const spec = newSpec("sma", { period: 50, source: "close" });
    expect(specToQueryFragment(spec)).toBe("sma:50");
  });

  it("specToQueryFragment includes :source when non-default", () => {
    const spec = newSpec("sma", { period: 20, source: "hl2" });
    expect(specToQueryFragment(spec)).toBe("sma:20:hl2");
  });

  it("specsToQueryParam joins visible specs only", () => {
    const a = newSpec("ema", { period: 21 });
    const b = { ...newSpec("sma", { period: 50 }), visible: false };
    const c = newSpec("hma", { period: 21 });
    expect(specsToQueryParam([a, b, c])).toBe("ema:21,hma:21");
  });

  it("newSpec returns unique ids on successive calls", () => {
    const a = newSpec("ema");
    const b = newSpec("ema");
    expect(a.id).not.toEqual(b.id);
  });

  it("newSpec applies overrides over defaults", () => {
    const s = newSpec("hma", { period: 50, weight: 3 });
    expect(s.period).toBe(50);
    expect(s.weight).toBe(3);
    expect(s.source).toBe(DEFAULTS.hma.source);
  });

  it("isValidPeriod enforces 2..500 integer", () => {
    expect(isValidPeriod(1)).toBe(false);
    expect(isValidPeriod(2)).toBe(true);
    expect(isValidPeriod(500)).toBe(true);
    expect(isValidPeriod(501)).toBe(false);
    expect(isValidPeriod(2.5)).toBe(false);
    expect(isValidPeriod(Number.NaN)).toBe(false);
  });

  it("storageKey is per-symbol and upper-cased", () => {
    expect(storageKey("ng")).toBe("ngti.chart.indicators.NG");
    expect(storageKey("CL")).toBe("ngti.chart.indicators.CL");
  });
});
