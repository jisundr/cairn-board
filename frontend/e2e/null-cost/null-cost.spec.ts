import { expect, test } from "@playwright/test";

test("a null session cost makes the task unknown, not a partial sum", async ({ page }) => {
  await page.goto("/");
  const metered = page.getByTestId("task-card-docs/tasks/2026-10-01-0900-build-metered").getByTestId("kcard-cost");
  await expect(metered).toHaveText("cost unknown");
  await expect(page.getByText("$2.00")).toHaveCount(0);
  // A task whose sessions are all priced still shows its figure.
  await expect(page.getByTestId("task-card-docs/tasks/2026-10-02-0900-build-fine").getByTestId("kcard-cost")).toHaveText("$0.40");
});
