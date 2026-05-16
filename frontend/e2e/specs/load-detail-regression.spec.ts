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

test("delete document cancels optional hydration and refreshes documents only", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const requests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/")) {
      requests.push(`${request.method()} ${url.pathname}`);
    }
  });
  page.on("dialog", (dialog) => dialog.accept());

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expectCoreLoadDetail(page);

  requests.length = 0;
  await page.getByRole("button", { name: "Delete" }).first().click();
  await expect(page.getByText("Deleted successfully.")).toBeVisible();

  expect(requests.filter((entry) => entry.includes("/documents/") && entry.startsWith("DELETE")).length).toBe(1);
  expect(requests).toContain(`GET /api/v1/loads/${seed.load.id}/documents`);
  expect(requests.some((entry) => entry.includes("packet-audit"))).toBe(false);
  expect(requests.some((entry) => entry.includes("submission-packets"))).toBe(false);
  expect(requests.some((entry) => entry.includes("review-queue"))).toBe(false);
  expect(requests.some((entry) => entry.includes("payment-reconciliation"))).toBe(false);
});

test("double-click delete sends one delete request", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let deleteRequests = 0;
  await page.route("**/api/v1/documents/*", async (route) => {
    if (route.request().method() === "DELETE") {
      deleteRequests += 1;
    }
    await route.fallback();
  });
  page.on("dialog", (dialog) => dialog.accept());

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expectCoreLoadDetail(page);

  const deleteButton = page.getByRole("button", { name: "Delete" }).first();
  await Promise.all([deleteButton.click(), deleteButton.click({ force: true })]);
  await expect(page.getByText("Deleted successfully.")).toBeVisible();
  expect(deleteRequests).toBe(1);
});

test("mobile optional hydration runs at max one idle request and zero during delete", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let activeOptional = 0;
  let maxActiveOptional = 0;
  let optionalDuringDelete = 0;
  let deleteInFlight = false;
  const optionalPattern = /\/(packet-audit|submission-packets|payment-reconciliation|review-queue\/loads\/.*\/context|invoice-status|documents)(\?|$|\/)/;

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const isOptional = route.request().method() === "GET" && optionalPattern.test(url.pathname);
    if (route.request().method() === "DELETE" && url.pathname.includes("/documents/")) {
      deleteInFlight = true;
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.fallback();
      deleteInFlight = false;
      return;
    }
    if (isOptional) {
      activeOptional += 1;
      maxActiveOptional = Math.max(maxActiveOptional, activeOptional);
      if (deleteInFlight) optionalDuringDelete += 1;
      await new Promise((resolve) => setTimeout(resolve, 120));
      await route.fallback();
      activeOptional -= 1;
      return;
    }
    await route.fallback();
  });
  page.on("dialog", (dialog) => dialog.accept());

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expectCoreLoadDetail(page);
  await page.waitForTimeout(1200);

  await page.getByRole("button", { name: "Delete" }).first().click();
  await expect(page.getByText("Deleted successfully.")).toBeVisible();

  expect(maxActiveOptional).toBeLessThanOrEqual(1);
  expect(optionalDuringDelete).toBe(0);
});
