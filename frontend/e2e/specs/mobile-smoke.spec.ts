import { expect, test } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test("mobile smoke: landing and driver load detail actions visible", async ({ page }) => {
  await mockApi(page);

  await page.goto("/");
  await expect(page.getByRole("link", { name: "Create Workspace" })).toBeVisible();
  await expect(page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth + 1)).resolves.toBeTruthy();

  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill("driver.e2e@example.com");
  await page.locator("input[type='password']").fill("Password123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.goto("/driver-portal/loads/load-e2e-001");
  await expect(page.getByRole("heading", { name: /Load/ })).toBeVisible();
  await expect(page.getByText(/Document Uploads/)).toBeVisible();
});
