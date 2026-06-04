import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";

const pushMock = vi.fn();
let mockSearchParams = new URLSearchParams();
const mockPathname = "/dashboard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => mockPathname,
  useSearchParams: () => mockSearchParams,
}));

import {
  ACTIVE_INSTRUMENT_STORAGE_KEY,
  DEFAULT_SYMBOL,
  readActiveSymbolFromSearchParams,
  useActiveInstrument,
} from "../useActiveInstrument";

beforeEach(() => {
  pushMock.mockReset();
  mockSearchParams = new URLSearchParams();
  localStorage.clear();
});

describe("useActiveInstrument — read order", () => {
  it("returns default NG when URL + localStorage are empty", () => {
    const { result } = renderHook(() => useActiveInstrument());
    expect(result.current.activeSymbol).toBe(DEFAULT_SYMBOL);
  });

  it("returns URL ?symbol= when present", () => {
    mockSearchParams = new URLSearchParams("symbol=CL");
    const { result } = renderHook(() => useActiveInstrument());
    expect(result.current.activeSymbol).toBe("CL");
  });

  it("falls back to localStorage when URL has no symbol", () => {
    localStorage.setItem(ACTIVE_INSTRUMENT_STORAGE_KEY, "CL");
    const { result } = renderHook(() => useActiveInstrument());
    expect(result.current.activeSymbol).toBe("CL");
  });

  it("URL takes precedence over localStorage", () => {
    mockSearchParams = new URLSearchParams("symbol=NG");
    localStorage.setItem(ACTIVE_INSTRUMENT_STORAGE_KEY, "CL");
    const { result } = renderHook(() => useActiveInstrument());
    expect(result.current.activeSymbol).toBe("NG");
  });
});

describe("useActiveInstrument — setActiveSymbol", () => {
  it("pushes a new URL with ?symbol= and writes to localStorage", () => {
    const { result } = renderHook(() => useActiveInstrument());
    act(() => result.current.setActiveSymbol("CL"));
    expect(pushMock).toHaveBeenCalledWith("/dashboard?symbol=CL");
    expect(localStorage.getItem(ACTIVE_INSTRUMENT_STORAGE_KEY)).toBe("CL");
  });

  it("normalizes lowercase input to uppercase", () => {
    const { result } = renderHook(() => useActiveInstrument());
    act(() => result.current.setActiveSymbol("cl"));
    expect(pushMock).toHaveBeenCalledWith("/dashboard?symbol=CL");
  });

  it("preserves other query params when switching", () => {
    mockSearchParams = new URLSearchParams("limit=20&horizon=1d");
    const { result } = renderHook(() => useActiveInstrument());
    act(() => result.current.setActiveSymbol("CL"));
    const pushed = pushMock.mock.calls[0][0] as string;
    expect(pushed).toContain("/dashboard?");
    expect(pushed).toContain("symbol=CL");
    expect(pushed).toContain("limit=20");
    expect(pushed).toContain("horizon=1d");
  });
});

describe("readActiveSymbolFromSearchParams (server-side helper)", () => {
  it("returns default when searchParams is undefined", () => {
    expect(readActiveSymbolFromSearchParams(undefined)).toBe(DEFAULT_SYMBOL);
  });

  it("returns default when symbol is absent", () => {
    expect(readActiveSymbolFromSearchParams({})).toBe(DEFAULT_SYMBOL);
    expect(readActiveSymbolFromSearchParams({ symbol: undefined })).toBe(
      DEFAULT_SYMBOL,
    );
  });

  it("returns the symbol uppercased when present as a string", () => {
    expect(readActiveSymbolFromSearchParams({ symbol: "cl" })).toBe("CL");
    expect(readActiveSymbolFromSearchParams({ symbol: "NG" })).toBe("NG");
  });

  it("returns default when symbol is an array (Next can pass arrays for repeated params)", () => {
    expect(readActiveSymbolFromSearchParams({ symbol: ["CL", "NG"] })).toBe(
      DEFAULT_SYMBOL,
    );
  });
});
