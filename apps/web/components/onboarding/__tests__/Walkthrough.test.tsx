import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const pushMock = vi.fn();
const mockPathname = "/dashboard";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => mockPathname,
}));

import { WalkthroughButton } from "../WalkthroughButton";
import { WalkthroughProvider } from "../WalkthroughProvider";
import { DASHBOARD_TOUR } from "../steps";

function Harness({ children }: { children?: React.ReactNode }) {
  return (
    <WalkthroughProvider>
      <WalkthroughButton />
      {children}
    </WalkthroughProvider>
  );
}

beforeEach(() => {
  pushMock.mockReset();
  localStorage.clear();
});

describe("WalkthroughButton + Provider", () => {
  it("renders the trigger button", () => {
    render(<Harness />);
    expect(screen.getByTestId("walkthrough-button")).toBeInTheDocument();
  });

  it("opens the tour on click and shows the welcome step", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    expect(screen.getByTestId("walkthrough-tooltip")).toBeInTheDocument();
    expect(screen.getByText(/Welcome to Goldeneye/)).toBeInTheDocument();
  });

  it("advances to the next step on Next click", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    // Step 2's title is "Watchlist".
    expect(screen.getByText("Watchlist")).toBeInTheDocument();
  });

  it("closes on Skip", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    fireEvent.click(screen.getByRole("button", { name: /Skip walkthrough/i }));
    expect(screen.queryByTestId("walkthrough-tooltip")).not.toBeInTheDocument();
  });

  it("closes on Escape key", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    expect(screen.getByTestId("walkthrough-tooltip")).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(screen.queryByTestId("walkthrough-tooltip")).not.toBeInTheDocument();
  });

  it("persists completion to localStorage on close", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    fireEvent.click(screen.getByRole("button", { name: /Skip walkthrough/i }));
    expect(localStorage.getItem("goldeneye:walkthrough-completed")).toBe("1");
  });

  it("renders progress dots — one per step in DASHBOARD_TOUR", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    const tooltip = screen.getByTestId("walkthrough-tooltip");
    // Each dot is a span with role aria-hidden + bg-* class.  Match by structure:
    // 4-px-wide bars under the heading.
    const dots = tooltip.querySelectorAll("span[aria-hidden='true']");
    // There's also the ─── eyebrow line and dotgroup spans — count by classname.
    const realDots = Array.from(dots).filter((el) =>
      el.classList.contains("w-4"),
    );
    expect(realDots).toHaveLength(DASHBOARD_TOUR.length);
  });

  it("Last step shows Done and clicking it closes the tour", async () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("walkthrough-button"));
    // Advance to the last step via Next clicks.
    for (let i = 0; i < DASHBOARD_TOUR.length - 1; i++) {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    }
    expect(screen.getByText("You're set")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Done/i }));
    expect(screen.queryByTestId("walkthrough-tooltip")).not.toBeInTheDocument();
  });
});
