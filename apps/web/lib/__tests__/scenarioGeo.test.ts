import {
  benchmarkOf,
  buildGlobeLayers,
  hasScenarioGeography,
  infraGeography,
  networkCorridors,
} from "../scenarioGeo";

// B5 honest degradation: only NG/BZ have a scenario geography. ES/ZN (and any
// non-energy asset class) must render NOTHING — never the Henry-Hub / Brent
// geography they have no business showing.
describe("scenarioGeo cross-asset gate (B5)", () => {
  it("NG and BZ keep their geography (unchanged)", () => {
    expect(hasScenarioGeography("NG")).toBe(true);
    expect(hasScenarioGeography("BZ")).toBe(true);
    expect(benchmarkOf("NG")).toBe("Henry Hub");
    expect(benchmarkOf("BZ")).toBe("Brent");
    expect(infraGeography("NG").length).toBeGreaterThan(0);
    expect(infraGeography("BZ").length).toBeGreaterThan(0);
  });

  it.each(["ES", "ZN", "GC"])(
    "%s has no geography: empty layers, no infra/corridors, no benchmark",
    (sym) => {
      expect(hasScenarioGeography(sym)).toBe(false);
      const { points, arcs } = buildGlobeLayers([], undefined, sym);
      expect(points).toEqual([]);
      expect(arcs).toEqual([]);
      expect(infraGeography(sym)).toEqual([]);
      expect(networkCorridors(sym)).toEqual([]);
      expect(benchmarkOf(sym)).toBe("");
    },
  );
});
