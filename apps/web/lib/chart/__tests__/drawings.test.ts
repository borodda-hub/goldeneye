import { beforeEach, describe, expect, it } from "vitest";
import {
  type Drawing,
  POINTS_NEEDED,
  distanceToHline,
  distanceToRectBorder,
  distanceToSegment,
  loadDrawings,
  newDrawingId,
  saveDrawings,
} from "../drawings";

describe("drawing geometry", () => {
  it("distanceToSegment: 0 on the segment, perpendicular off it", () => {
    const a = { x: 0, y: 0 };
    const b = { x: 10, y: 0 };
    expect(distanceToSegment({ x: 5, y: 0 }, a, b)).toBe(0);
    expect(distanceToSegment({ x: 5, y: 3 }, a, b)).toBeCloseTo(3);
    // beyond an endpoint clamps to the endpoint distance
    expect(distanceToSegment({ x: 13, y: 4 }, a, b)).toBeCloseTo(5);
  });

  it("distanceToSegment: zero-length segment = distance to the point", () => {
    const a = { x: 2, y: 2 };
    expect(distanceToSegment({ x: 5, y: 6 }, a, a)).toBeCloseTo(5);
  });

  it("distanceToHline: vertical distance only", () => {
    expect(distanceToHline({ x: 999, y: 10 }, 4)).toBe(6);
  });

  it("distanceToRectBorder: 0 on an edge, >0 inside", () => {
    const a = { x: 0, y: 0 };
    const b = { x: 10, y: 10 };
    expect(distanceToRectBorder({ x: 5, y: 0 }, a, b)).toBe(0); // on top edge
    expect(distanceToRectBorder({ x: 5, y: 5 }, a, b)).toBeCloseTo(5); // center
  });
});

describe("drawing persistence", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips drawings per symbol", () => {
    const d: Drawing[] = [
      {
        id: newDrawingId(),
        type: "trendline",
        points: [
          { time: 1, price: 3.4 },
          { time: 2, price: 3.5 },
        ],
        color: "#c9a35c",
        width: 2,
      },
    ];
    saveDrawings("NG", d);
    expect(loadDrawings("NG")).toEqual(d);
    expect(loadDrawings("CL")).toEqual([]); // per-symbol isolation
  });

  it("returns [] for missing / malformed storage", () => {
    expect(loadDrawings("ZZ")).toEqual([]);
    localStorage.setItem("goldeneye:chart:drawings:ZZ", "not json");
    expect(loadDrawings("ZZ")).toEqual([]);
  });

  it("newDrawingId is unique-ish", () => {
    expect(newDrawingId()).not.toBe(newDrawingId());
  });

  it("POINTS_NEEDED covers every drawing type", () => {
    expect(POINTS_NEEDED.hline).toBe(1);
    expect(POINTS_NEEDED.trendline).toBe(2);
    expect(POINTS_NEEDED.rectangle).toBe(2);
    expect(POINTS_NEEDED.fib).toBe(2);
  });
});
