import type { Shock } from "@/app/(app)/scenarios/types";
import { netLean, shockLean } from "../scenarioLean";

describe("shockLean", () => {
  it("weather: colder → bullish, warmer → bearish", () => {
    expect(
      shockLean({ type: "weather", region: "ne", delta_temp_f: -8, days: 10 }),
    ).toBe("bullish");
    expect(
      shockLean({ type: "weather", region: "ne", delta_temp_f: 8, days: 10 }),
    ).toBe("bearish");
  });

  it("lng_export: more offtake → bullish, disruption → bearish", () => {
    expect(shockLean({ type: "lng_export", delta_bcfd: 2, days: 14 })).toBe(
      "bullish",
    );
    expect(shockLean({ type: "lng_export", delta_bcfd: -1.5, days: 14 })).toBe(
      "bearish",
    );
  });

  it("production: more supply → bearish, freeze-off → bullish", () => {
    expect(shockLean({ type: "production", delta_bcfd: 2, days: 7 })).toBe(
      "bearish",
    );
    expect(shockLean({ type: "production", delta_bcfd: -2, days: 7 })).toBe(
      "bullish",
    );
  });

  it("storage: build → bearish, draw → bullish", () => {
    expect(shockLean({ type: "storage", delta_bcf: 30, days: 7 })).toBe(
      "bearish",
    );
    expect(shockLean({ type: "storage", delta_bcf: -20, days: 7 })).toBe(
      "bullish",
    );
  });

  it("opec_supply: cut → bullish, raise → bearish", () => {
    expect(shockLean({ type: "opec_supply", delta_mbpd: -1.5, days: 90 })).toBe(
      "bullish",
    );
    expect(shockLean({ type: "opec_supply", delta_mbpd: 1.0, days: 90 })).toBe(
      "bearish",
    );
  });

  it("geopolitical_supply: outage → bullish, restored → bearish", () => {
    expect(
      shockLean({
        type: "geopolitical_supply",
        region: "hormuz",
        delta_mbpd: -3,
        days: 14,
      }),
    ).toBe("bullish");
    expect(
      shockLean({
        type: "geopolitical_supply",
        region: "hormuz",
        delta_mbpd: 3,
        days: 14,
      }),
    ).toBe("bearish");
  });

  it("demand: more demand → bullish, slowdown → bearish", () => {
    expect(
      shockLean({ type: "demand", region: "china", delta_mbpd: 1.5, days: 60 }),
    ).toBe("bullish");
    expect(
      shockLean({
        type: "demand",
        region: "china",
        delta_mbpd: -1.8,
        days: 60,
      }),
    ).toBe("bearish");
  });

  it("inventory: draw → bullish, build/SPR release → bearish", () => {
    expect(shockLean({ type: "inventory", delta_mmbbl: -25, days: 14 })).toBe(
      "bullish",
    );
    expect(shockLean({ type: "inventory", delta_mmbbl: 60, days: 30 })).toBe(
      "bearish",
    );
  });
});

describe("netLean", () => {
  it("tallies and resolves the net direction", () => {
    const shocks: Shock[] = [
      { type: "weather", region: "ne", delta_temp_f: -8, days: 10 }, // bullish
      { type: "storage", delta_bcf: -20, days: 7 }, // bullish
      { type: "production", delta_bcfd: 2, days: 7 }, // bearish
    ];
    const r = netLean(shocks);
    expect(r.bullish).toBe(2);
    expect(r.bearish).toBe(1);
    expect(r.lean).toBe("bullish");
  });

  it("ties resolve to neutral; empty is neutral", () => {
    expect(netLean([]).lean).toBe("neutral");
    const tie: Shock[] = [
      { type: "storage", delta_bcf: -10, days: 7 }, // bullish
      { type: "storage", delta_bcf: 10, days: 7 }, // bearish
    ];
    expect(netLean(tie).lean).toBe("neutral");
  });
});
