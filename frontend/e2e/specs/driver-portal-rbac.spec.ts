import path from "node:path";

import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { mockApi } from "../support/mock-api";
import { attachRuntimeGuards } from "../support/test-guards";

test("driver portal workflow + RBAC restrictions", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await mockApi(page);

  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill(seed.driver.email);
  await page.locator("input[type='password']").fill(seed.driver.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/driver-portal/);

  await page.goto("/driver-portal/loads");
  await expect(page.getByRole("heading", { name: "My Loads" })).toBeVisible();
  await expect(page.getByText(seed.load.load_number)).toBeVisible();

  await page.goto(`/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByText(/What is missing/i)).toBeVisible();

  await page.locator('input[type="file"]').first().setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-invalid.txt"));
  await expect(page.getByText(/only PDF or image files are allowed/i)).toBeVisible();

  await page.locator('input[type="file"]').first().setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-pod.png"));
  await expect(page.getByText(/upload success/i)).toBeVisible();

  await page.goto("/dashboard/money");
  await expect(page).toHaveURL(/\/driver-portal/);

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page).toHaveURL(/\/driver-portal/);

  await assertClean();
});
