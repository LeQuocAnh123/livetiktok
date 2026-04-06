import { test, expect } from "@playwright/test";

const MOCK_SETTINGS = {
  tone: "friendly",
  blacklist_keywords: ["spam"],
  reply_delay_min: 5,
  reply_delay_max: 15,
  user_cooldown_seconds: 60,
  max_replies_per_session: 500,
  auto_reply_enabled: true,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/settings/**", (route) => {
    const method = route.request().method();
    if (method === "GET") {
      route.fulfill({ json: MOCK_SETTINGS });
    } else if (method === "PUT") {
      route.fulfill({ json: { ...MOCK_SETTINGS, tone: "professional" } });
    } else {
      route.continue();
    }
  });
  await page.route("**/api/v1/settings/test-reply", (route) => {
    route.fulfill({ json: { reply: "Dạ shop có ạ!", intent: "product_inquiry", chunks_used: ["c1"] } });
  });
});

test("settings page loads and shows current settings", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByLabel(/tone/i)).toHaveValue("friendly");
  await expect(page.getByText("Auto Reply")).toBeVisible();
});

test("can update settings", async ({ page }) => {
  await page.goto("/settings");
  const toneInput = page.getByLabel(/tone/i);
  await toneInput.fill("professional");
  await page.getByRole("button", { name: /save settings/i }).click();
  await expect(page.getByText(/saved/i)).toBeVisible({ timeout: 3000 });
});

test("can run test-reply", async ({ page }) => {
  await page.goto("/settings");
  await page.getByPlaceholder(/enter a test comment/i).fill("Còn hàng không?");
  await page.getByRole("button", { name: /test reply/i }).click();
  await expect(page.getByText("Dạ shop có ạ!")).toBeVisible({ timeout: 3000 });
});
