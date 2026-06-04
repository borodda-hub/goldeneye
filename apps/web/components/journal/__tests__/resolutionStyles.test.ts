import { resolutionLabel, resolutionStripeClass } from "../resolutionStyles";

describe("resolutionStripeClass", () => {
  it("returns empty string when resolution is null", () => {
    expect(resolutionStripeClass(null)).toBe("");
  });

  it("returns up-colored stripe for hit", () => {
    expect(resolutionStripeClass("hit")).toMatch(/border-l-up/);
  });

  it("returns down-colored stripe for miss", () => {
    expect(resolutionStripeClass("miss")).toMatch(/border-l-down/);
  });

  it("returns flat-colored stripe for neutral", () => {
    expect(resolutionStripeClass("neutral")).toMatch(/border-l-flat/);
  });

  it("returns conf-low-colored stripe for unresolved", () => {
    expect(resolutionStripeClass("unresolved")).toMatch(/border-l-conf-low/);
  });
});

describe("resolutionLabel", () => {
  it("returns 'Pending resolution' for null", () => {
    expect(resolutionLabel(null)).toBe("Pending resolution");
  });

  it("capitalizes the resolution value", () => {
    expect(resolutionLabel("hit")).toBe("Hit");
    expect(resolutionLabel("miss")).toBe("Miss");
    expect(resolutionLabel("neutral")).toBe("Neutral");
    expect(resolutionLabel("unresolved")).toBe("Unresolved");
  });
});
