import { expect, test } from "@playwright/test";

test("dashboard: disclaimer visible, metrics render, live dot connects", async ({
  page,
}) => {
  await page.goto("/dashboard");

  // Disclaimer text visible in footer
  await expect(
    page.getByText("research and decision-support prototype"),
  ).toBeVisible();

  // HeaderRow has the NG symbol rendered
  await expect(page.getByText("NG", { exact: true }).first()).toBeVisible();

  // LiveDot connects within 5 seconds (aria-label changes to Connected)
  await expect(page.getByLabel("Connected")).toBeVisible({ timeout: 5000 });
});
