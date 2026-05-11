import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { RunButton } from "../RunButton";

describe("RunButton", () => {
  it("renders default label when idle", () => {
    render(<RunButton disabled={false} running={false} onRun={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent(/Run Scenario/i);
  });

  it("shows running state", () => {
    render(<RunButton disabled={false} running={true} onRun={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent(/Running/i);
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  });

  it("calls onRun when clicked and enabled", () => {
    const onRun = vi.fn();
    render(<RunButton disabled={false} running={false} onRun={onRun} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onRun).toHaveBeenCalledTimes(1);
  });

  it("does not call onRun when disabled", () => {
    const onRun = vi.fn();
    render(<RunButton disabled={true} running={false} onRun={onRun} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onRun).not.toHaveBeenCalled();
  });

  it("does not call onRun when running", () => {
    const onRun = vi.fn();
    render(<RunButton disabled={false} running={true} onRun={onRun} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onRun).not.toHaveBeenCalled();
  });
});
