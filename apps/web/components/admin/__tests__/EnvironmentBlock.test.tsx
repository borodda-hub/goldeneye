import { render, screen } from "@testing-library/react";
import { EnvironmentBlock } from "../EnvironmentBlock";

describe("EnvironmentBlock", () => {
  it("renders git sha and build time", () => {
    render(
      <EnvironmentBlock
        gitSha="abc1234"
        buildTime="2026-05-11T08:00:00Z"
        envFlags={{}}
      />,
    );
    expect(screen.getByText("abc1234")).toBeInTheDocument();
    expect(screen.getByText("2026-05-11T08:00:00Z")).toBeInTheDocument();
  });

  it("renders dashes when sha and build time are missing", () => {
    render(<EnvironmentBlock envFlags={{}} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("shows env flag presence with check or circle", () => {
    render(
      <EnvironmentBlock
        envFlags={{
          DATABASE_URL: true,
          REDIS_URL: false,
        }}
      />,
    );
    expect(screen.getByText("✓ set")).toBeInTheDocument();
    expect(screen.getByText("○ unset")).toBeInTheDocument();
  });

  it("never renders env var values, only presence", () => {
    const { container } = render(
      <EnvironmentBlock
        envFlags={{ DATABASE_URL: true }}
      />,
    );
    // No env values should leak through — only "✓ set" or "○ unset"
    expect(container.textContent).not.toContain("postgresql");
    expect(container.textContent).not.toContain("redis://");
  });
});
