import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/dashboard",
}));

import { ONBOARDING_STEPS, markSeen, markStep } from "@/lib/onboarding";
import { GettingStarted } from "../GettingStarted";
import { GettingStartedChip } from "../GettingStartedChip";
import { WalkthroughProvider } from "../WalkthroughProvider";
import { WelcomeModal } from "../WelcomeModal";

function Harness() {
  return (
    <WalkthroughProvider>
      <WelcomeModal />
      <GettingStartedChip />
      <GettingStarted />
    </WalkthroughProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
  pushMock.mockReset();
});

describe("WelcomeModal", () => {
  it("shows on first run and hides after 'Explore on my own'", () => {
    render(<Harness />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("welcome-explore"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not show once seen", () => {
    markSeen();
    render(<Harness />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("'Take the 2-min tour' marks seen and launches the walkthrough", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("welcome-take-tour"));
    expect(
      screen.queryByRole("dialog", { name: "Welcome to Goldeneye" }),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("walkthrough-tooltip")).toBeInTheDocument();
  });
});

describe("GettingStarted checklist", () => {
  it("appears once seen and reflects done flags", () => {
    markSeen();
    markStep("thesis");
    render(<Harness />);
    expect(
      screen.getByLabelText("Getting started checklist"),
    ).toBeInTheDocument();
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("does not appear before the welcome is dismissed", () => {
    render(<Harness />);
    expect(
      screen.queryByLabelText("Getting started checklist"),
    ).not.toBeInTheDocument();
  });

  it("hides at 5/5", () => {
    markSeen();
    for (const s of ONBOARDING_STEPS) markStep(s.id);
    render(<Harness />);
    expect(
      screen.queryByLabelText("Getting started checklist"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("getting-started-chip"),
    ).not.toBeInTheDocument();
  });

  it("dismiss hides the card; the chip re-opens it", () => {
    markSeen();
    render(<Harness />);
    fireEvent.click(screen.getByLabelText("Dismiss checklist"));
    expect(
      screen.queryByLabelText("Getting started checklist"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("getting-started-chip"));
    expect(
      screen.getByLabelText("Getting started checklist"),
    ).toBeInTheDocument();
  });
});
