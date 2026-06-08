import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { SignalViewControls } from "../SignalViewControls";

describe("SignalViewControls", () => {
  it("renders all three views and both estimators by default", () => {
    render(
      <SignalViewControls
        view="both"
        onViewChange={() => {}}
        estimator="ewma"
        onEstimatorChange={() => {}}
      />,
    );
    expect(screen.getByText("Both")).toBeInTheDocument();
    expect(screen.getByText("Range")).toBeInTheDocument();
    expect(screen.getByText("Direction")).toBeInTheDocument();
    expect(screen.getByText("EWMA")).toBeInTheDocument();
    expect(screen.getByText("log-HAR")).toBeInTheDocument();
  });

  it("hides the estimator selector in direction-only view (no co-equal framing)", () => {
    render(
      <SignalViewControls
        view="direction"
        onViewChange={() => {}}
        estimator="ewma"
        onEstimatorChange={() => {}}
      />,
    );
    expect(screen.queryByText("EWMA")).not.toBeInTheDocument();
    expect(screen.queryByText("Vol estimator")).not.toBeInTheDocument();
  });

  it("emits view and estimator changes", () => {
    const onView = vi.fn();
    const onEstimator = vi.fn();
    render(
      <SignalViewControls
        view="both"
        onViewChange={onView}
        estimator="ewma"
        onEstimatorChange={onEstimator}
      />,
    );
    fireEvent.click(screen.getByText("Range"));
    fireEvent.click(screen.getByText("log-HAR"));
    expect(onView).toHaveBeenCalledWith("range");
    expect(onEstimator).toHaveBeenCalledWith("har_log");
  });
});
