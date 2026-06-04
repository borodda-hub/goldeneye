import type { DqCoachingResponse } from "@/lib/api";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useDqCoachingMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useDqCoaching: (...args: unknown[]) => useDqCoachingMock(...args),
}));

import { DQCoachPanel } from "../DQCoachPanel";

function _coaching(
  overrides: Partial<DqCoachingResponse> = {},
): DqCoachingResponse {
  return {
    instrument_code: "NG",
    buckets: [
      {
        label: "60-80",
        effective_patterns: [
          "weather skill on cold snaps",
          "tight invalidation",
        ],
        failure_patterns: ["overweighted LNG export claims"],
        recommendation: "Score weather skill before sizing.",
      },
    ],
    overall: {
      synthesis:
        "Your 60-80% bucket calibrates well on weather but drifts on LNG.",
      top_recommendation: "Tighten invalidation criteria on LNG-driven theses.",
    },
    safety: {
      confidence: "medium",
      caveats: ["Small sample caveat."],
      as_of: "2026-05-12T12:00:00Z",
      disclaimer: "Goldeneye is a research and decision-support terminal.",
    },
    ...overrides,
  };
}

const refetchMock = vi.fn();

beforeEach(() => {
  useDqCoachingMock.mockReset();
  refetchMock.mockReset();
});

describe("DQCoachPanel", () => {
  it("shows a loading state", () => {
    useDqCoachingMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: refetchMock,
      isFetching: true,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText(/Synthesizing coaching/)).toBeInTheDocument();
  });

  it("renders the empty state when buckets + overall are empty", () => {
    useDqCoachingMock.mockReturnValue({
      data: _coaching({
        buckets: [],
        overall: { synthesis: "", top_recommendation: "" },
      }),
      isLoading: false,
      error: null,
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText(/at least 3 journal entries/)).toBeInTheDocument();
    expect(screen.getByText(/Small sample caveat/)).toBeInTheDocument();
  });

  it("renders overall synthesis + top recommendation", () => {
    useDqCoachingMock.mockReturnValue({
      data: _coaching(),
      isLoading: false,
      error: null,
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText(/calibrates well on weather/)).toBeInTheDocument();
    expect(
      screen.getByText(/Tighten invalidation criteria/),
    ).toBeInTheDocument();
  });

  it("renders per-bucket cards with effective and failure patterns", () => {
    useDqCoachingMock.mockReturnValue({
      data: _coaching(),
      isLoading: false,
      error: null,
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText("Bucket 60-80%")).toBeInTheDocument();
    expect(screen.getByText(/weather skill on cold snaps/)).toBeInTheDocument();
    expect(
      screen.getByText(/overweighted LNG export claims/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Score weather skill before sizing/),
    ).toBeInTheDocument();
  });

  it("renders the safety disclaimer at the bottom", () => {
    useDqCoachingMock.mockReturnValue({
      data: _coaching(),
      isLoading: false,
      error: null,
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText(/Goldeneye is a research/)).toBeInTheDocument();
  });

  it("re-run button calls refetch", () => {
    useDqCoachingMock.mockReturnValue({
      data: _coaching(),
      isLoading: false,
      error: null,
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    fireEvent.click(screen.getByRole("button", { name: /Re-run coaching/i }));
    expect(refetchMock).toHaveBeenCalled();
  });

  it("renders an error state with a retry button", () => {
    useDqCoachingMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("API error 500"),
      refetch: refetchMock,
      isFetching: false,
    });
    render(<DQCoachPanel />);
    expect(screen.getByText(/Failed to load coaching/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetchMock).toHaveBeenCalled();
  });
});
