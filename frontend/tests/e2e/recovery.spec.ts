import { expect, test } from "@playwright/test";

/**
 * End-to-end UI scenario. Drives backend state through real endpoints and asserts the UI renders
 * backend truth across the journey — including the cycle-17 reopening and the verified outcome.
 *
 * Prereqs: backend on :8000 and frontend on :3000 running; `npx playwright install chromium`.
 */
test("verified recovery journey — cycle-17 reopen → verified", async ({ page, request }) => {
  // 1. Reset to the scenario start.
  await request.post("/api/demo/reset");

  // 2. Mission Control shows the active mission at INTERVENTION_RECORDED.
  await page.goto("/missions");
  await expect(page.getByRole("heading", { name: "Mission Control" })).toBeVisible();
  await expect(page.getByText("INC-2841")).toBeVisible();
  await expect(page.getByText("Intervention recorded")).toBeVisible();

  // 3. Open the mission; the progress rail + responsibilities render.
  await page.goto("/missions/INC-2841?tab=overview");
  await expect(page.getByText("Agent responsibility")).toBeVisible();
  await expect(page.getByText("Human responsibility")).toBeVisible();

  // 4. Drive the full scenario through real backend endpoints.
  const run = await request.post("/api/demo/run");
  expect((await run.json()).final_state).toBe("VERIFIED_RECOVERY");

  // 5. Verification timeline shows the cycle-17 reveal (non-theatrical, accessible).
  await page.goto("/missions/INC-2841?tab=timeline");
  await expect(page.getByText(/Recovery Contract violated at cycle 17/)).toBeVisible();
  await expect(page.getByText(/Recovery not proven/)).toBeVisible();
  await expect(page.locator('svg[role="img"]').first()).toBeVisible();

  // 6. Outcome shows verified recovery, before/after, and a PENDING knowledge candidate.
  await page.goto("/missions/INC-2841?tab=outcome");
  await expect(page.getByText("Production recovery verified.")).toBeVisible();
  await expect(page.getByText("F27 absent for 30 cycles")).toBeVisible();
  await expect(page.getByText(/Pending expert review/)).toBeVisible();
});

test("role authorization is reflected in the UI", async ({ page, request }) => {
  await request.post("/api/demo/reset");
  await request.post("/api/incidents/INC-2841/contract/draft");

  // As a technician, the contract-review (supervisor) action must not be offered as approvable.
  await page.goto("/missions/INC-2841?tab=overview");
  await page.evaluate(() => localStorage.setItem("vra-role", "technician"));
  await page.reload();
  await expect(page.getByText(/supervisor must review and approve/i)).toBeVisible();
});
