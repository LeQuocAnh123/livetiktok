import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/sessions/status", (route) => {
    route.fulfill({ json: { connected: false, session: null } });
  });
  await page.route("**/api/v1/sessions/start", (route) => {
    route.fulfill({
      json: {
        connected: true,
        session: { id: "s1", seller_id: "s1", status: "active", started_at: new Date().toISOString() },
      },
    });
  });
  await page.route("**/api/v1/sessions/stop", (route) => {
    route.fulfill({ json: { message: "Session stopped" } });
  });
});

test("monitor page loads with session offline status", async ({ page }) => {
  await page.goto("/monitor");
  await expect(page.getByText(/offline/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /start session/i })).toBeVisible();
});

test("can start a session", async ({ page }) => {
  await page.goto("/monitor");
  await page.getByRole("button", { name: /start session/i }).click();
  await expect(page.getByRole("button", { name: /stop session/i })).toBeVisible({ timeout: 3000 });
});

test("can stop an active session", async ({ page }) => {
  await page.route("**/api/v1/sessions/status", (route) => {
    route.fulfill({
      json: {
        connected: true,
        session: { id: "s1", seller_id: "s1", status: "active", started_at: new Date().toISOString() },
      },
    });
  });
  await page.goto("/monitor");
  await expect(page.getByRole("button", { name: /stop session/i })).toBeVisible();
  await page.getByRole("button", { name: /stop session/i }).click();
  await expect(page.getByRole("button", { name: /start session/i })).toBeVisible({ timeout: 3000 });
});
