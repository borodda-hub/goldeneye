import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { NewsFeedPanel } from "../NewsFeedPanel";

const useRecentNewsMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  useRecentNews: (...args: unknown[]) => useRecentNewsMock(...args),
}));

function _events(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    published_at: new Date(Date.now() - i * 3600_000).toISOString(),
    source: i % 2 === 0 ? "eia_today_in_energy" : "yahoo_finance_ng",
    headline: `Test headline ${i}`,
    body: "body",
    category: i % 3 === 0 ? "storage" : "weather",
    impact_score: 0.5,
    url: `https://example.com/${i}`,
  }));
}

beforeEach(() => {
  useRecentNewsMock.mockReset();
});

describe("NewsFeedPanel", () => {
  it("renders a loading state", () => {
    useRecentNewsMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText(/Loading news/)).toBeInTheDocument();
  });

  it("renders an error state", () => {
    useRecentNewsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText(/News feed unavailable/)).toBeInTheDocument();
  });

  it("renders an empty state when no events", () => {
    useRecentNewsMock.mockReturnValue({
      data: { events: [], count: 0 },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText(/No recent NG-relevant items/)).toBeInTheDocument();
  });

  it("renders headlines with clickable links", () => {
    useRecentNewsMock.mockReturnValue({
      data: { events: _events(3), count: 3 },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText("Test headline 0")).toBeInTheDocument();
    const link0 = screen.getByText("Test headline 0").closest("a");
    expect(link0).toHaveAttribute("href", "https://example.com/0");
    expect(link0).toHaveAttribute("target", "_blank");
    expect(link0).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("humanizes source identifiers", () => {
    useRecentNewsMock.mockReturnValue({
      data: { events: _events(2), count: 2 },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText("EIA")).toBeInTheDocument();
    expect(screen.getByText("Yahoo Finance")).toBeInTheDocument();
  });

  it("renders relative timestamps", () => {
    useRecentNewsMock.mockReturnValue({
      data: { events: _events(2), count: 2 },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    // index 0 is ~now → "just now" or "<1m ago" branch
    expect(screen.getByText(/just now|0m ago|1m ago/)).toBeInTheDocument();
    // index 1 is ~1h ago.
    expect(screen.getByText(/1h ago/)).toBeInTheDocument();
  });

  it("renders the source attribution footer", () => {
    useRecentNewsMock.mockReturnValue({
      data: { events: _events(1), count: 1 },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText(/Sources: EIA/)).toBeInTheDocument();
    expect(screen.getByText(/Yahoo Finance/i)).toBeInTheDocument();
  });

  it("falls back to plain text when an event has no url", () => {
    useRecentNewsMock.mockReturnValue({
      data: {
        events: [
          {
            published_at: new Date().toISOString(),
            source: "eia_today_in_energy",
            headline: "Unlinked item",
            url: null,
            category: "other",
          },
        ],
        count: 1,
      },
      isLoading: false,
      isError: false,
    });
    render(<NewsFeedPanel />);
    expect(screen.getByText("Unlinked item")).toBeInTheDocument();
    expect(screen.getByText("Unlinked item").closest("a")).toBeNull();
  });
});
