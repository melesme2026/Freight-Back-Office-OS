import { expect, test, type Page, type Request } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";

async function expectCoreLoadDetail(page: Page) {
  await expect(page.getByRole("main").getByRole("heading", { name: seed.load.load_number })).toBeVisible();
  await expect(page.getByText("Unable to load load detail")).toHaveCount(0);
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("load detail renders when optional endpoints timeout", async ({ page }) => {
  await page.route("**/api/v1/loads/*/packet-audit", async (route) => {
    await route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Packet audit timed out" } }),
    });
  });
  await page.route("**/api/v1/loads/*/submission-packets", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 504,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "Submission packets timed out" } }),
      });
      return;
    }
    await route.fallback();
  });
  await page.route("**/api/v1/carrier-profile", async (route) => {
    await route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Carrier profile timed out" } }),
    });
  });

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);

  await expectCoreLoadDetail(page);
  await expect(page.getByText("Packet audit timed out")).toBeVisible();
  await expect(page.getByText("Submission packets timed out")).toBeVisible();
  await expect(page.getByText("Carrier profile timed out")).toBeVisible();
});

test("load detail does not fail if packet audit times out", async ({ page }) => {
  await page.route("**/api/v1/loads/*/packet-audit", async (route) => {
    await route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Packet audit timed out" } }),
    });
  });

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);

  await expectCoreLoadDetail(page);
  await expect(page.getByText("Packet audit timed out")).toBeVisible();
});

test("load detail does not fail if documents endpoint times out", async ({ page }) => {
  await page.route(/\/api\/v1\/loads\/[^/]+\/documents(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Documents timed out" } }),
    });
  });

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);

  await expectCoreLoadDetail(page);
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(page.getByText("Documents timed out")).toBeVisible();
});

test("auth token is included in load detail requests", async ({ page }) => {
  const loadDetailRequests: Request[] = [];
  await page.route(`**/api/v1/loads/${seed.load.id}`, async (route) => {
    loadDetailRequests.push(route.request());
    await route.fallback();
  });

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);

  await expectCoreLoadDetail(page);
  expect(loadDetailRequests.length).toBeGreaterThan(0);
  for (const request of loadDetailRequests) {
    expect(request.headers().authorization).toMatch(/^Bearer\s+.+/);
  }
});

test("login redirect does not trigger excessive dashboard request storm", async ({ page }) => {
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/") && request.method() !== "OPTIONS") {
      apiRequests.push(`${request.method()} ${url.pathname}`);
    }
  });

  await loginAsOwner(page);
  await page.waitForLoadState("networkidle");

  expect(apiRequests.length, apiRequests.join("\n")).toBeLessThanOrEqual(8);
});
