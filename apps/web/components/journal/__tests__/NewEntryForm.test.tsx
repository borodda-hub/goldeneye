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
});
