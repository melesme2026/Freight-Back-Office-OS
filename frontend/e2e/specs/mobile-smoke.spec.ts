import { expect, test, type Page } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { loginAsDriver, loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";

async function expectNoPageOverflow(page: Page) {
  await expect(
    page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth + 1)
  ).resolves.toBeTruthy();
}

test("mobile smoke: landing and driver load detail actions visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);

  await page.goto("/");
  await expect(page.getByRole("link", { name: "Create Workspace" })).toBeVisible();
  await expectNoPageOverflow(page);

  await loginAsDriver(page);
  await page.goto(`/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByRole("main").getByRole("heading", { name: /Load/ })).toBeVisible();
  await expect(page.getByText(/Document Uploads/)).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: owner dashboard, loads, and load detail do not page-overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockApi(page);

  await loginAsOwner(page);
  await expect(page.getByRole("navigation").getByRole("link", { name: "Loads" })).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto("/dashboard/loads");
  await expect(page.getByRole("heading", { name: "Loads" })).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page.getByRole("heading", { name: /Load/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: driver portal overview and uploads remain touch-friendly", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await mockApi(page);

  await loginAsDriver(page);
  await expect(page.getByRole("heading", { name: "Driver Workspace" })).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto("/driver-portal/uploads");
  await expect(page.getByRole("heading", { name: /Upload Documents/ })).toBeVisible();
  await expect(page.getByLabel("File or photo")).toBeVisible();
  await expectNoPageOverflow(page);
});
