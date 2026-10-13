import { expect, test } from "@playwright/test";

const PARENT = "docs/tasks/2026-10-01-0900-build-epic";
const LIVE = `${PARENT}/02-build-board`;

test("renders cards in their phase columns with cost per task", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId(`task-card-${PARENT}`)).toBeVisible();

  const column = (title: string) => page.locator(".kanban-column", { hasText: title });
  await expect(column("Parent tasks").getByTestId(`task-card-${PARENT}`)).toBeVisible();
  await expect(column("Planned").getByTestId("task-card-docs/tasks/2026-10-02-1000-build-planned-thing")).toBeVisible();
  await expect(column("Done").getByTestId(`task-card-${PARENT}/01-build-schema`)).toBeVisible();

  // Sole sessions s-2 (1.25) + s-3 (0.75), and s-1 on the done child.
  await expect(page.getByTestId(`task-card-${LIVE}`).getByTestId("kcard-cost")).toHaveText("$2.00");
  await expect(page.getByTestId(`task-card-${PARENT}/01-build-schema`).getByTestId("kcard-cost")).toHaveText("$0.50");
  await expect(page.getByTestId(`task-card-${PARENT}`).getByTestId("kcard-cost")).toHaveCount(0);
});

test("lights the card named by a live marker and flags needs-attention", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId(`task-card-${LIVE}`).getByText("active")).toBeVisible();
  await expect(page.getByTestId("attention-pill")).toHaveText("1 need attention");
});

test("opens the drawer from the folder's own files and lists its docs", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId(`task-card-${LIVE}`).click();
  const drawer = page.getByTestId("task-drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Board child");
  await expect(drawer).toContainText("$2.00");
  await expect(page).toHaveURL(/task=/);

  await page.getByTestId("drawer-tab-docs").click();
  await page.getByTestId("docs-file-REQUIREMENTS.md").click();
  await expect(drawer).toContainText("Seeded requirements for Board child");
});

test("serves no write routes", async ({ request }) => {
  const res = await request.post("/api/tasks", { data: {} });
  expect(res.status()).toBe(405);
});
