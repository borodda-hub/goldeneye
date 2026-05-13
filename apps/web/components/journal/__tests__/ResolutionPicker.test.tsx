import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

const mutateMock = vi.fn();

vi.mock("@/lib/queries", () => ({
  usePatchJournalEntry: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}));

import { ResolutionPicker } from "../ResolutionPicker";

beforeEach(() => {
  mutateMock.mockReset();
});

describe("ResolutionPicker", () => {
  it("renders the four options", () => {
    render(<ResolutionPicker entryId="e1" value={null} />);
    for (const label of ["Unresolved", "Hit", "Miss", "Neutral"]) {
      expect(screen.getByRole("radio", { name: label })).toBeInTheDocument();
    }
  });

  it("marks the currently-resolved option as checked", () => {
    render(<ResolutionPicker entryId="e1" value="hit" />);
    expect(screen.getByRole("radio", { name: "Hit" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "Miss" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("marks Unresolved as checked when value is null", () => {
    render(<ResolutionPicker entryId="e1" value={null} />);
    expect(screen.getByRole("radio", { name: "Unresolved" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("calls mutate with the picked value on click", () => {
    render(<ResolutionPicker entryId="e1" value={null} />);
    fireEvent.click(screen.getByRole("radio", { name: "Miss" }));
    expect(mutateMock).toHaveBeenCalledWith(
      { id: "e1", body: { resolved_direction: "miss" } },
      expect.any(Object),
    );
  });

  it("calls mutate with null when Unresolved is picked", () => {
    render(<ResolutionPicker entryId="e1" value="hit" />);
    fireEvent.click(screen.getByRole("radio", { name: "Unresolved" }));
    expect(mutateMock).toHaveBeenCalledWith(
      { id: "e1", body: { resolved_direction: null } },
      expect.any(Object),
    );
  });

  it("does not mutate when the same option is clicked again", () => {
    render(<ResolutionPicker entryId="e1" value="hit" />);
    fireEvent.click(screen.getByRole("radio", { name: "Hit" }));
    expect(mutateMock).not.toHaveBeenCalled();
  });
});
