import { test, expect } from "@playwright/test";

const MOCK_LIST = {
  items: [
    { id: "c1", seller_id: "s1", content: "Áo cotton giá 150k", category: "product", metadata: {}, needs_reembed: false },
  ],
  total: 1,
  page: 1,
  limit: 20,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/knowledge/**", (route) => {
    const method = route.request().method();
    const url = route.request().url();
    if (method === "GET") {
      route.fulfill({ json: MOCK_LIST });
    } else if (method === "POST" && url.includes("/api/v1/knowledge/") && !url.includes("upload")) {
      route.fulfill({
        status: 201,
        json: { id: "c-new", seller_id: "s1", content: "New chunk", category: "faq", metadata: {}, needs_reembed: true },
      });
    } else if (method === "PUT") {
      route.fulfill({ json: { id: "c1", seller_id: "s1", content: "Updated", category: "product", metadata: {}, needs_reembed: true } });
    } else if (method === "DELETE") {
      route.fulfill({ status: 204, body: "" });
    } else {
      route.continue();
    }
  });
});

test("knowledge page loads and shows chunks", async ({ page }) => {
  await page.goto("/knowledge");
  await expect(page.getByText("Áo cotton giá 150k")).toBeVisible();
  await expect(page.getByText("product")).toBeVisible();
});

test("can open create chunk dialog", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /add chunk/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel(/content/i)).toBeVisible();
});

test("can create a new chunk", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /add chunk/i }).click();
  await page.getByLabel(/content/i).fill("New chunk content");
  await page.getByRole("button", { name: /save/i }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("can delete a chunk", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /delete/i }).first().click();
  await page.getByRole("button", { name: /confirm/i }).click();
  await expect(page.getByText(/error/i)).not.toBeVisible();
});
