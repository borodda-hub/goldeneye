import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const mutateMock = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({
    mutate: mutateMock,
    isPending: false,
    isError: false,
    error: null,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}));

import { NewEntryForm } from "../NewEntryForm";

describe("NewEntryForm", () => {
  beforeEach(() => {
    mutateMock.mockClear();
  });

  it("renders heading and submit button", () => {
    render(<NewEntryForm />);
    expect(screen.getByText("New Entry")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Submit Entry/i }),
    ).toBeInTheDocument();
  });

  it("disables submit button when hypothesis is empty", () => {
    render(<NewEntryForm />);
    const btn = screen.getByRole("button", { name: /Submit Entry/i });
    expect(btn).toBeDisabled();
  });

  it("enables submit button when hypothesis is filled", () => {
    render(<NewEntryForm />);
    const ta = screen.getByPlaceholderText(/What do you expect to happen/);
    fireEvent.change(ta, { target: { value: "Hypothesis text" } });
    const btn = screen.getByRole("button", { name: /Submit Entry/i });
    expect(btn).not.toBeDisabled();
  });

  it("can add and remove evidence rows", () => {
    render(<NewEntryForm />);
    fireEvent.click(screen.getByRole("button", { name: /\+ Add/i }));
    expect(screen.getByPlaceholderText("source")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Remove evidence 1"));
    expect(screen.queryByPlaceholderText("source")).not.toBeInTheDocument();
  });

  it("renders confidence slider with default 50%", () => {
    render(<NewEntryForm />);
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("shows the Resolvable Claim section with an extract action", () => {
    render(<NewEntryForm />);
    expect(screen.getByText("Resolvable Claim")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Extract from thesis/i }),
    ).toBeInTheDocument();
  });

  it("'+ Manual' reveals editable direction / horizon / threshold fields", () => {
    render(<NewEntryForm />);
    // empty state — no claim fields yet
    expect(
      screen.queryByLabelText("Predicted direction"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /\+ Manual/i }));
    expect(screen.getByLabelText("Predicted direction")).toBeInTheDocument();
    expect(screen.getByLabelText("Horizon in days")).toBeInTheDocument();
    expect(screen.getByLabelText("Threshold percent")).toBeInTheDocument();
    // defaults from the manual seed
    expect(screen.getByLabelText("Horizon in days")).toHaveValue(14);
  });
});
