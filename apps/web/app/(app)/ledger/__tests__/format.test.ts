import {
  asNumber,
  asRecord,
  asString,
  decisionHypothesis,
  decisionTimestamp,
  fmtDateTime,
  fmtFraction,
  fmtPrice,
} from "../format";
import type { LedgerDecision, LedgerEvent } from "../types";

function evt(partial: Partial<LedgerEvent>): LedgerEvent {
  return {
    seq: 1,
    decision_id: "d1",
    event_type: "created",
    occurred_at: "2026-06-10T12:00:00Z",
    recorded_at: "2026-06-10T12:00:00Z",
    source: "live",
    payload: {},
    prev_hash: null,
    row_hash: "h",
    ...partial,
  };
}

describe("safe narrowing helpers", () => {
  it("asRecord rejects arrays and non-objects", () => {
    expect(asRecord({ a: 1 })).toEqual({ a: 1 });
    expect(asRecord([1, 2])).toEqual({});
    expect(asRecord("x")).toEqual({});
    expect(asRecord(null)).toEqual({});
  });

  it("asString / asNumber are type-strict", () => {
    expect(asString("ok")).toBe("ok");
    expect(asString(3)).toBeNull();
    expect(asNumber(3.5)).toBe(3.5);
    expect(asNumber(Number.NaN)).toBeNull();
    expect(asNumber("3")).toBeNull();
  });
});

describe("decisionHypothesis", () => {
  it("reads the hypothesis from the created event", () => {
    const d: LedgerDecision = {
      decision_id: "d1",
      chain_ok: true,
      broken_at_seq: null,
      events: [
        evt({
          event_type: "created",
          payload: {
            user_inputs: { hypothesis: "Cold snap tightens balances" },
          },
        }),
      ],
    };
    expect(decisionHypothesis(d)).toBe("Cold snap tightens balances");
  });

  it("falls back when no created event / hypothesis", () => {
    const d: LedgerDecision = {
      decision_id: "d1",
      chain_ok: true,
      broken_at_seq: null,
      events: [evt({ event_type: "resolved", payload: { outcome: "hit" } })],
    };
    expect(decisionHypothesis(d)).toMatch(/no hypothesis/);
  });
});

describe("decisionTimestamp", () => {
  it("prefers the created event's occurred_at", () => {
    const d: LedgerDecision = {
      decision_id: "d1",
      chain_ok: true,
      broken_at_seq: null,
      events: [
        evt({ event_type: "resolved", occurred_at: "2026-06-20T09:00:00Z" }),
        evt({ event_type: "created", occurred_at: "2026-06-10T12:00:00Z" }),
      ],
    };
    expect(decisionTimestamp(d)).toBe("2026-06-10T12:00:00Z");
  });
});

describe("formatters", () => {
  it("fmtDateTime trims to minutes", () => {
    expect(fmtDateTime("2026-06-10T12:34:56Z")).toBe("2026-06-10 12:34");
    expect(fmtDateTime(null)).toBe("—");
  });

  it("fmtFraction renders a signed percent", () => {
    expect(fmtFraction(0.0342)).toBe("+3.42%");
    expect(fmtFraction(-0.01)).toBe("-1.00%");
    expect(fmtFraction(null)).toBe("—");
  });

  it("fmtPrice fixes to 3 dp", () => {
    expect(fmtPrice(3.5)).toBe("3.500");
    expect(fmtPrice(null)).toBe("—");
  });
});
