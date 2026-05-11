import { test, expect } from "@playwright/test";

const FORBIDDEN_PHRASES = [
  "guaranteed",
  "guarantee",
  "will profit",
  "sure thing",
  "risk-free",
  "no risk",
  "buy now",
  "sell now",
  "go long",
  "go short",
  "you should buy",
  "you should sell",
  "i recommend",
  "my recommendation",
  "this is a buy",
  "this is a sell",
  "hot tip",
  "moonshot",
  "to the moon",
];

test.describe("Signals page", () => {
  test("loads within 2s and renders at least one model card", async ({
    page,
  }) => {
    const startTime = Date.now();
    await page.goto("/signals");
    await expect(
      page.locator("text=moving average").first(),
    ).toBeVisible({ timeout: 2000 });
    expect(Date.now() - startTime).toBeLessThan(2000);
  });

  test("SafetyEnvelopeNote or disclaimer is present", async ({ page }) => {
    await page.goto("/signals");
    await expect(
      page.locator("text=/NGTI is a research/i").first(),
    ).toBeVisible();
  });

  test("no forbidden phrases in rendered content", async ({ page }) => {
    await page.goto("/signals");
    const content = (await page.content()).toLowerCase();
    for (const phrase of FORBIDDEN_PHRASES) {
      expect(content).not.toContain(phrase.toLowerCase());
    }
  });

  test("page reloads are stable (5 reloads)", async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await page.goto("/signals");
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
