import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InlineMarkdown } from "../InlineMarkdown";

describe("InlineMarkdown", () => {
  it("renders **bold** as <strong> and *italic* as <em>", () => {
    const { container } = render(
      <InlineMarkdown text="Storage draw **exceeds consensus** and *appears* supportive." />,
    );
    expect(container.querySelector("strong")?.textContent).toBe(
      "exceeds consensus",
    );
    expect(container.querySelector("em")?.textContent).toBe("appears");
    // The literal asterisks are consumed, not shown.
    expect(container.textContent).not.toContain("*");
  });

  it("never injects HTML — markup in model output renders as literal text", () => {
    const { container } = render(
      <InlineMarkdown text={"<img src=x onerror=alert(1)> **<b>bold</b>**"} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    // The tag text survives as visible literal text inside the strong.
    expect(container.querySelector("strong")?.textContent).toBe("<b>bold</b>");
    expect(screen.getByText(/<img src=x onerror=alert\(1\)>/)).toBeTruthy();
  });

  it("leaves unpaired/other markdown as literal text", () => {
    const { container } = render(
      <InlineMarkdown text="a * b remains, and ## headers stay literal" />,
    );
    expect(container.textContent).toBe(
      "a * b remains, and ## headers stay literal",
    );
    expect(container.querySelector("strong")).toBeNull();
  });
});
