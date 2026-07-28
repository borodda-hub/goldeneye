import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const postConciergeChatMock = vi.fn();
vi.mock("@/lib/api", () => ({
  postConciergeChat: (...args: unknown[]) => postConciergeChatMock(...args),
}));
vi.mock("@/lib/clerk", () => ({ clerkEnabled: false }));
vi.mock("@/lib/useActiveInstrument", () => ({
  useActiveInstrument: () => ({
    activeSymbol: "NG",
    setActiveSymbol: () => {},
  }),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

import { ConciergeWidget } from "../ConciergeWidget";

function renderWidget() {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ConciergeWidget />
    </QueryClientProvider>,
  );
}

describe("ConciergeWidget", () => {
  it("is closed by default and opens with a grounded greeting", () => {
    renderWidget();
    expect(
      screen.queryByRole("region", { name: /goldeneye concierge/i }),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /open concierge/i }));
    expect(
      screen.getByRole("region", { name: /goldeneye concierge/i }),
    ).toBeTruthy();
    expect(screen.getByText(/What would you like to explore/)).toBeTruthy();
    // The honesty microcopy is always visible in the panel footer.
    expect(screen.getByText(/never financial advice/i)).toBeTruthy();
  });

  it("sends route + symbol with the message and renders reply + suggestion chips", async () => {
    postConciergeChatMock.mockResolvedValue({
      reply: "The **range band** is the validated product (see /dashboard).",
      suggestions: [{ route: "/validation", label: "Validation" }],
      safety: { confidence: "low", caveats: [], as_of: "", disclaimer: "d" },
    });
    renderWidget();
    fireEvent.click(screen.getByRole("button", { name: /open concierge/i }));
    fireEvent.change(screen.getByLabelText(/message the concierge/i), {
      target: { value: "what is the band?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() =>
      expect(screen.getByText(/validated product/)).toBeTruthy(),
    );
    expect(postConciergeChatMock).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "what is the band?",
        symbol: "NG",
        route: "/dashboard",
      }),
    );
    // Markdown renders as <strong>, not literal asterisks (InlineMarkdown).
    expect(screen.getByText("range band").tagName).toBe("STRONG");
    const chip = screen.getByRole("link", { name: /validation/i });
    expect(chip.getAttribute("href")).toBe("/validation");
  });

  it("shows a graceful error bubble on failure", async () => {
    postConciergeChatMock.mockRejectedValue(new Error("HTTP 500"));
    renderWidget();
    fireEvent.click(screen.getByRole("button", { name: /open concierge/i }));
    fireEvent.change(screen.getByLabelText(/message the concierge/i), {
      target: { value: "hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() =>
      expect(screen.getByText(/couldn't answer that just now/i)).toBeTruthy(),
    );
  });
});
