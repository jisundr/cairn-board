import { expect, test } from "@playwright/test";

test("names cairn core when no exports exist", async ({ page }) => {
  await page.goto("/");
  const state = page.getByTestId("kanban-no-export");
  await expect(state).toBeVisible();
  await expect(state).toContainText("cairn core");
  await expect(state).toContainText("Install cairn");
  await expect(page.getByTestId("kcard-cost")).toHaveCount(0);
  await expect(page.locator(".kcard")).toHaveCount(0);
});
