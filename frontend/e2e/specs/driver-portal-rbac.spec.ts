import path from "node:path";

import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { gotoProtectedDriverRoute, loginAsDriver, loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";
import { attachRuntimeGuards } from "../support/test-guards";

test("driver portal workflow + RBAC restrictions", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await mockApi(page);

  await loginAsDriver(page);

  await gotoProtectedDriverRoute(page, "/driver-portal/loads");
  await expect(page.getByRole("heading", { name: "My Loads" })).toBeVisible();
  await expect(page.getByText(seed.load.load_number)).toBeVisible();

  await gotoProtectedDriverRoute(page, `/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByText(/What is missing/i)).toBeVisible();

  await page.getByLabel("Upload Proof of Delivery file or photo", { exact: true }).setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-invalid.txt"));
  await expect(page.getByText(/only PDF or image files are allowed/i)).toBeVisible();

  await page.getByLabel("Upload Proof of Delivery file or photo", { exact: true }).setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-pod.png"));
  await expect(page.getByText(/upload success/i)).toBeVisible();

  await page.goto("/dashboard/money");
  await expect(page).toHaveURL(/\/driver-portal/);

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page).toHaveURL(/\/driver-portal/);

  await assertClean();
});

test("staff session stays on dedicated Driver Login instead of redirecting to dashboard", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await mockApi(page);

  await loginAsOwner(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Driver Login", exact: true }).first().click();

  await expect(page).toHaveURL(/\/driver-login/);
  await expect(page.getByRole("heading", { name: "Driver Sign in" })).toBeVisible();
  await expect(page.getByText(/signed in to the staff app/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /sign out and use driver login/i })).toBeVisible();

  await assertClean();
});
