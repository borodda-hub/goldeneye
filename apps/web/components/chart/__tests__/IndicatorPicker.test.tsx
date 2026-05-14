import { newSpec } from "@/lib/chart/indicatorRegistry";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IndicatorPicker } from "../IndicatorPicker";

function baseProps(
  overrides: Partial<React.ComponentProps<typeof IndicatorPicker>> = {},
) {
  return {
    open: true,
    onClose: vi.fn(),
    indicators: [],
    onAdd: vi.fn(),
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
    onToggleVisible: vi.fn(),
    ...overrides,
  };
}

describe("IndicatorPicker", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <IndicatorPicker {...baseProps({ open: false })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the modal heading when open", () => {
    render(<IndicatorPicker {...baseProps()} />);
    expect(
      screen.getByRole("dialog", { name: /indicators/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/add indicator/i)).toBeInTheDocument();
  });

  it("lists all 7 MA types in the type dropdown", () => {
    render(<IndicatorPicker {...baseProps()} />);
    const select = screen.getByLabelText("Indicator type");
    const options = (select as HTMLSelectElement).options;
    const values = Array.from(options).map((o) => o.value);
    expect(values).toEqual([
      "sma",
      "ema",
      "wma",
      "hma",
      "dema",
      "tema",
      "vwma",
    ]);
  });

  it("calls onAdd with a fresh spec when Add is clicked", () => {
    const onAdd = vi.fn();
    render(<IndicatorPicker {...baseProps({ onAdd })} />);

    fireEvent.change(screen.getByLabelText("Indicator type"), {
      target: { value: "hma" },
    });
    fireEvent.change(screen.getByLabelText("Period"), {
      target: { value: "55" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^add$/i }));

    expect(onAdd).toHaveBeenCalledTimes(1);
    const spec = onAdd.mock.calls[0][0];
    expect(spec.type).toBe("hma");
    expect(spec.period).toBe(55);
    expect(spec.visible).toBe(true);
    expect(spec.id).toMatch(/^ind_/);
  });

  it("blocks Add when period is out of range", () => {
    const onAdd = vi.fn();
    render(<IndicatorPicker {...baseProps({ onAdd })} />);

    fireEvent.change(screen.getByLabelText("Period"), {
      target: { value: "1" },
    });
    const addBtn = screen.getByRole("button", { name: /^add$/i });
    expect(addBtn).toBeDisabled();
    fireEvent.click(addBtn);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("Edit pre-fills the form and calls onUpdate", () => {
    const onUpdate = vi.fn();
    const existing = newSpec("sma", { period: 50 });
    render(
      <IndicatorPicker {...baseProps({ indicators: [existing], onUpdate })} />,
    );

    fireEvent.click(screen.getByLabelText("Edit SMA(50)"));
    // Heading swaps
    expect(screen.getByText(/edit indicator/i)).toBeInTheDocument();
    // Form is pre-filled
    expect(
      (screen.getByLabelText("Indicator type") as HTMLSelectElement).value,
    ).toBe("sma");
    expect((screen.getByLabelText("Period") as HTMLInputElement).value).toBe(
      "50",
    );

    fireEvent.change(screen.getByLabelText("Period"), {
      target: { value: "200" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onUpdate).toHaveBeenCalledTimes(1);
    const spec = onUpdate.mock.calls[0][0];
    expect(spec.id).toBe(existing.id); // same id, not a new one
    expect(spec.period).toBe(200);
  });

  it("Delete calls onDelete with the spec id", () => {
    const onDelete = vi.fn();
    const existing = newSpec("ema", { period: 21 });
    render(
      <IndicatorPicker {...baseProps({ indicators: [existing], onDelete })} />,
    );
    fireEvent.click(screen.getByLabelText("Delete EMA(21)"));
    expect(onDelete).toHaveBeenCalledWith(existing.id);
  });

  it("Hide/Show toggle calls onToggleVisible", () => {
    const onToggleVisible = vi.fn();
    const existing = newSpec("ema", { period: 21 });
    render(
      <IndicatorPicker
        {...baseProps({ indicators: [existing], onToggleVisible })}
      />,
    );
    fireEvent.click(screen.getByLabelText("Hide"));
    expect(onToggleVisible).toHaveBeenCalledWith(existing.id);
  });

  it("hidden indicator shows 'Show' affordance + line-through label", () => {
    const hidden = { ...newSpec("ema", { period: 21 }), visible: false };
    render(<IndicatorPicker {...baseProps({ indicators: [hidden] })} />);
    expect(screen.getByLabelText("Show")).toBeInTheDocument();
  });

  it("empty state copy when no indicators yet", () => {
    render(<IndicatorPicker {...baseProps()} />);
    expect(screen.getByText(/no indicators yet/i)).toBeInTheDocument();
  });

  it("Escape key calls onClose", () => {
    const onClose = vi.fn();
    render(<IndicatorPicker {...baseProps({ onClose })} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
