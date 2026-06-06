import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const useCurrentThesisMock = vi.fn();
const useThesisSeedMock = vi.fn();
const useCreateThesisMock = vi.fn();
const usePatchThesisMock = vi.fn();
const useCritiqueThesisMock = vi.fn();
const useDevilsAdvocateMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useCurrentThesis: (...args: unknown[]) => useCurrentThesisMock(...args),
  useThesisSeed: (...args: unknown[]) => useThesisSeedMock(...args),
  useCreateThesis: (...args: unknown[]) => useCreateThesisMock(...args),
  usePatchThesis: (...args: unknown[]) => usePatchThesisMock(...args),
  useCritiqueThesis: (...args: unknown[]) => useCritiqueThesisMock(...args),
  useDevilsAdvocate: (...args: unknown[]) => useDevilsAdvocateMock(...args),
}));

import { WorkingThesisCard } from "../WorkingThesisCard";

function _sampleThesis() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    instrument_code: "NG",
    statement:
      "Storage draws should exceed the five-year average through late March.",
    supporting_evidence: [
      {
        factor: "weather_demand",
        weight: 0.7,
        note: "NE cold",
        source: "moving_average_directional",
      },
      {
        factor: "lng_export_stable",
        weight: 0.4,
        note: "",
        source: "volatility_regime",
      },
    ],
    contradicting_evidence: [
      {
        factor: "production_up",
        weight: 0.3,
        note: "",
        source: "prophet_trend",
      },
    ],
    missing_data: ["EIA Weekly Storage", "NWS 6-10 day"],
    conviction_pct: 72,
    created_at: "2026-05-12T08:00:00Z",
    updated_at: "2026-05-12T11:00:00Z",
    active: true,
  };
}

beforeEach(() => {
  // The card now defaults collapsed (Phase 19, fits a fresh dashboard on one
  // screen). These tests assert body content, so render it expanded.
  localStorage.setItem("goldeneye:dashboard:working-thesis-collapsed", "0");

  useCurrentThesisMock.mockReset();
  useThesisSeedMock.mockReset();
  useCreateThesisMock.mockReset();
  usePatchThesisMock.mockReset();
  useCritiqueThesisMock.mockReset();
  useDevilsAdvocateMock.mockReset();
  useDevilsAdvocateMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      counter_thesis: "Deficit may be priced in.",
      premortem: ["Production rebounds"],
      invalidation_signals: ["Smaller EIA print Thu"],
      safety: {
        confidence: "medium",
        caveats: ["A probe, not a verdict."],
        as_of: "2026-05-12T12:00:00Z",
        disclaimer: "Goldeneye is a research terminal.",
      },
    }),
    isPending: false,
    error: null,
  });

  useThesisSeedMock.mockReturnValue({ data: undefined, isLoading: false });
  useCreateThesisMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue(_sampleThesis()),
    isPending: false,
    error: null,
  });
  usePatchThesisMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue(_sampleThesis()),
    isPending: false,
    error: null,
  });
  useCritiqueThesisMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      missed_risks: ["LNG outage tail risk"],
      blind_spots: ["Assumes weather skill > day 7"],
      questions: ["What invalidates this in 7 days?"],
      safety: {
        confidence: "medium",
        caveats: ["Test caveat."],
        as_of: "2026-05-12T12:00:00Z",
        disclaimer: "Goldeneye is a research terminal.",
      },
    }),
    isPending: false,
    error: null,
  });
});

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <WorkingThesisCard />
    </QueryClientProvider>,
  );
}

describe("WorkingThesisCard", () => {
  it("renders the empty state when no active thesis", () => {
    useCurrentThesisMock.mockReturnValue({ data: null, isLoading: false });
    renderCard();
    expect(screen.getByText(/No working thesis yet/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Draft a thesis/i }),
    ).toBeInTheDocument();
  });

  it("renders the read view with statement and counts when a thesis exists", () => {
    useCurrentThesisMock.mockReturnValue({
      data: _sampleThesis(),
      isLoading: false,
    });
    renderCard();
    expect(
      screen.getByText(/Storage draws should exceed the five-year average/),
    ).toBeInTheDocument();
    // Conviction % visible.
    expect(screen.getByText("72%")).toBeInTheDocument();
    // Edit + Critique buttons available.
    expect(screen.getByRole("button", { name: /⚙ Edit/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /→ Critique/i }),
    ).toBeInTheDocument();
  });

  it("shows a loading skeleton while the query is fetching", () => {
    useCurrentThesisMock.mockReturnValue({ data: undefined, isLoading: true });
    renderCard();
    expect(screen.getByTestId("thesis-loading")).toBeInTheDocument();
  });

  it("opens the edit modal when the Edit button is clicked", () => {
    useCurrentThesisMock.mockReturnValue({
      data: _sampleThesis(),
      isLoading: false,
    });
    renderCard();
    fireEvent.click(screen.getByRole("button", { name: /⚙ Edit/i }));
    expect(
      screen.getByRole("dialog", { name: /Edit Working Thesis/i }),
    ).toBeInTheDocument();
  });

  it("opens the critique drawer when the Critique button is clicked", () => {
    useCurrentThesisMock.mockReturnValue({
      data: _sampleThesis(),
      isLoading: false,
    });
    renderCard();
    fireEvent.click(screen.getByRole("button", { name: /→ Critique/i }));
    expect(
      screen.getByRole("dialog", { name: /Thesis critique/i }),
    ).toBeInTheDocument();
  });
});
