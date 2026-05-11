import { render, screen } from "@testing-library/react";
import { DashboardLiveBar } from "../DashboardLiveBar";

vi.mock("@/lib/realtime", () => ({
  useChannel: vi.fn(() => ({ data: null, status: "disconnected" })),
}));

describe("DashboardLiveBar", () => {
  it("renders disconnected state correctly", () => {
    render(<DashboardLiveBar />);
    expect(screen.getByText("disconnected")).toBeInTheDocument();
  });

  it("renders connected state when status is connected", async () => {
    const { useChannel } = await import("@/lib/realtime");
    vi.mocked(useChannel).mockReturnValue({
      data: null,
      status: "connected",
    });
    render(<DashboardLiveBar />);
    expect(screen.getByText("connected")).toBeInTheDocument();
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });
});
