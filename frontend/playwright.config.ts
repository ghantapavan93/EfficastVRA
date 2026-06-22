import { defineConfig } from "@playwright/test";

// Assumes backend (http://localhost:8000) and frontend (http://localhost:3000) are already running.
// First time: `npx playwright install chromium`. Then: `npm run e2e`.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    trace: "on-first-retry",
  },
});
