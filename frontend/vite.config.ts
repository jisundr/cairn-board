import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// outDir points at ../static, which server.py serves alongside its JSON API.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    // jsdom's default "about:blank" origin throws on localStorage access.
    environmentOptions: { jsdom: { url: "http://localhost/" } },
    setupFiles: ["./src/setupTests.ts"],
    globals: true,
    // The Playwright specs in e2e/ use their own test runner.
    exclude: ["e2e/**", "node_modules/**"],
  },
});
