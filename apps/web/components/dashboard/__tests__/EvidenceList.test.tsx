import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { EvidenceList } from "../EvidenceList";

describe("EvidenceList", () => {
  it("renders 'None.' when items list is empty", () => {
    render(
      <EvidenceList
        label="Supporting evidence"
        items={[]}
        onChange={() => {}}
        tone="supporting"
      />,
    );
    expect(screen.getByText("None.")).toBeInTheDocument();
  });

  it("renders each factor and note", () => {
    render(
      <EvidenceList
        label="Supporting evidence"
        items={[
          { factor: "weather", weight: 0.5, note: "NE cold", source: null },
          { factor: "storage_draw", weight: 0.6, note: "", source: null },
        ]}
        onChange={() => {}}
        tone="supporting"
      />,
    );
    expect(screen.getByText("weather")).toBeInTheDocument();
    expect(screen.getByText(/NE cold/)).toBeInTheDocument();
    expect(screen.getByText("storage_draw")).toBeInTheDocument();
  });

  it("calls onChange with the new item appended when Add is clicked", () => {
    const onChange = vi.fn();
    render(
      <EvidenceList
        label="Supporting evidence"
        items={[]}
        onChange={onChange}
        tone="supporting"
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/Add a factor/), {
      target: { value: "new_factor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(onChange).toHaveBeenCalledWith([
      { factor: "new_factor", weight: null, note: "", source: null },
    ]);
  });

  it("calls onChange with the item removed when × is clicked", () => {
    const onChange = vi.fn();
    render(
      <EvidenceList
        label="Supporting evidence"
        items={[{ factor: "weather", weight: 0.5, note: "", source: null }]}
        onChange={onChange}
        tone="supporting"
      />,
    );
    fireEvent.click(screen.getByLabelText("Remove weather"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("supports adding via Enter key in the input", () => {
    const onChange = vi.fn();
    render(
      <EvidenceList
        label="Supporting"
        items={[]}
        onChange={onChange}
        tone="supporting"
      />,
    );
    const input = screen.getByPlaceholderText(/Add a factor/);
    fireEvent.change(input, { target: { value: "via_enter" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith([
      { factor: "via_enter", weight: null, note: "", source: null },
    ]);
  });
});
