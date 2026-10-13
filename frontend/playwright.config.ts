import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

// One server.py process per scenario, each with HOME pointed at its own
// scratch directory so the server cannot read this machine's real
// ~/.claude/cairn markers. `npm run build` must precede `playwright test`:
// server.py serves whatever is already in ../static.
const FRONTEND_ROOT = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(FRONTEND_ROOT, "..");
const SCRATCH = path.resolve(FRONTEND_ROOT, ".e2e-scratch");

const SCENARIOS = [
  { name: "populated", port: 4431 },
  { name: "tasks-only", port: 4432 },
  { name: "empty", port: 4433 },
  { name: "shared", port: 4434 },
  { name: "null-cost", port: 4435 },
];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: { trace: "on-first-retry" },
  projects: SCENARIOS.map((s) => ({
    name: s.name,
    testDir: `./e2e/${s.name}`,
    use: { ...devices["Desktop Chrome"], baseURL: `http://127.0.0.1:${s.port}` },
  })),
  webServer: SCENARIOS.map((s) => ({
    command: `python3 e2e/fixtures/seed.py "${SCRATCH}" ${s.name} && python3 "${REPO_ROOT}/server.py" "${SCRATCH}/${s.name}/board-demo" ${s.port}`,
    url: `http://127.0.0.1:${s.port}/api/projects`,
    cwd: FRONTEND_ROOT,
    env: { HOME: path.join(SCRATCH, s.name) },
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  })),
});
