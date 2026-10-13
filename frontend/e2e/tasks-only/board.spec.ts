import { expect, test } from "@playwright/test";

test("renders the board with no cost and no error when usage.json is absent", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("task-card-docs/tasks/2026-10-02-1000-build-planned-thing")).toBeVisible();
  await expect(page.getByTestId("kcard-cost")).toHaveCount(0);
  await expect(page.getByTestId("kanban-note")).toHaveCount(0);
  await expect(page.getByTestId("kanban-error-text")).toHaveCount(0);
  await expect(page.getByTestId("kanban-export-error")).toHaveCount(0);
});
