import { expect, test } from "@playwright/test";

test("a shared session is labelled, never split into either task", async ({ page }) => {
  await page.goto("/");
  const first = page.getByTestId("task-card-docs/tasks/2026-10-01-0900-build-first").getByTestId("kcard-cost");
  const second = page.getByTestId("task-card-docs/tasks/2026-10-02-0900-build-second").getByTestId("kcard-cost");
  // The $9.00 shared session appears in neither figure.
  await expect(first).toHaveText("$1.00 + 1 shared");
  await expect(second).toHaveText("shared session");
  await expect(page.getByText("$9.00")).toHaveCount(0);
  await expect(page.getByText("$5.00")).toHaveCount(0);
});
