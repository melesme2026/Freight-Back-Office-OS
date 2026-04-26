import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { loginAsDriver } from "../support/auth";
import { mockApi } from "../support/mock-api";

test("mobile smoke: landing and driver load detail actions visible", async ({ page }) => {
  await mockApi(page);

  await page.goto("/");
  await expect(page.getByRole("link", { name: "Create Workspace" })).toBeVisible();
  await expect(page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth + 1)).resolves.toBeTruthy();

  await loginAsDriver(page);
  await page.goto(`/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByRole("heading", { name: /Load/ })).toBeVisible();
  await expect(page.getByText(/Document Uploads/)).toBeVisible();
});
