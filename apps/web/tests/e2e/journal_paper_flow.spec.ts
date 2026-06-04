import { expect, test } from "@playwright/test";

test.describe("Journal + Paper trading flow", () => {
  test("create journal entry then open and close a paper trade", async ({
    page,
  }) => {
    // 1. Journal: create a new entry
    await page.goto("/journal");
    await expect(page.getByText("Decision Journal")).toBeVisible();

    await page
      .getByPlaceholder(/What do you expect to happen/)
      .fill("Cold snap rally setup");

    const slider = page.getByLabel(/Confidence percentage/);
    await slider.fill("65");

    await page.getByRole("button", { name: /Submit Entry/i }).click();

    // 2. Wait for the entry to appear in the list, then click it
    const card = page
      .getByTestId("journal-entry-card")
      .filter({ hasText: "Cold snap rally setup" })
      .first();
    await expect(card).toBeVisible({ timeout: 10000 });
    await card.click();

    // 3. Detail drawer with LLM review section visible
    const drawer = page.getByTestId("entry-detail-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText("LLM Review")).toBeVisible();

    // 4. Paper: open a new trade
    await page.goto("/paper");
    await expect(page.getByText("Paper Trading")).toBeVisible();

    await page.getByPlaceholder(/e.g. NGF26/).fill("NGF26");
    await page.getByRole("button", { name: /^Long$/i }).click();

    const size = page.getByLabel(/Size \(contracts\)/i);
    await size.fill("2");
    const entry = page.getByLabel(/Entry Price/i);
    await entry.fill("3.45");

    await page.getByTestId("open-trade-submit").click();

    // 5. New row appears in open positions
    const openRow = page.getByTestId("open-trade-row").first();
    await expect(openRow).toBeVisible({ timeout: 10000 });
    // MTM cell renders either "—" (no live tick yet) or a "$" amount
    await expect(openRow.getByTestId("mtm-pnl")).toBeVisible();

    // 6. Close the trade and verify it moves to closed table
    await openRow.getByTestId("close-trade-btn").click();
    await expect(page.getByTestId("closed-trade-row").first()).toBeVisible({
      timeout: 10000,
    });
  });
});
