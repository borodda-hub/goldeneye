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

test.describe("Scenario Lab page", () => {
  test("loads and renders template gallery", async ({ page }) => {
    await page.goto("/scenarios");
    await expect(page.getByText("Scenario Lab")).toBeVisible();
    await expect(page.getByText("Templates")).toBeVisible();
  });

  test("loads a template and populates shock builder", async ({ page }) => {
    await page.goto("/scenarios");
    await page.getByText(/Cold Snap/).first().click();
    await expect(page.getByText(/loaded/i).first()).toBeVisible();
    await expect(page.locator("text=Shock Builder")).toBeVisible();
  });

  test("running a scenario populates the result panel", async ({ page }) => {
    await page.goto("/scenarios");
    await page.getByText(/Cold Snap/).first().click();
    await page.getByRole("button", { name: /Run Scenario/i }).click();

    // Result panel populates with all six sub-sections
    await expect(page.getByText(/Result/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Timeframe/i)).toBeVisible();
    await expect(page.getByText(/Expected range/i)).toBeVisible();
    await expect(page.getByText(/Assumptions/i)).toBeVisible();
    await expect(page.getByText(/Counterarguments/i)).toBeVisible();
    await expect(page.getByText(/Data needed to validate/i)).toBeVisible();
    await expect(page.getByText(/Narrative/i)).toBeVisible();
  });

  test("no forbidden phrases over 25 reloads", async ({ page }) => {
    for (let i = 0; i < 25; i++) {
      await page.goto("/scenarios");
      const content = (await page.content()).toLowerCase();
      for (const phrase of FORBIDDEN_PHRASES) {
        expect(content).not.toContain(phrase.toLowerCase());
      }
    }
  });
});
