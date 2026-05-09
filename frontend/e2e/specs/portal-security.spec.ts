import path from "node:path";

import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { loginAsDriver, loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("protected dashboard routes redirect when unauthenticated", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?session=expired/);

  await page.goto("/driver-portal/loads");
  await expect(page).toHaveURL(/\/driver-login\?session=expired/);
});

test("owner logout clears access and browser back cannot reopen dashboard", async ({ page }) => {
  await loginAsOwner(page);
  await expect(page.getByText(seed.owner.email)).toBeVisible();

  await page.getByRole("button", { name: "Log Out" }).first().click();
  await expect(page).toHaveURL(/\/$/);
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("fbos_access_token"))).toBeNull();

  await page.goBack();
  await expect(page).toHaveURL(/\/login\?session=expired/);
});

test("driver denied from dashboard and logout clears driver portal access", async ({ page }) => {
  await loginAsDriver(page);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/driver-portal/);

  await page.getByRole("button", { name: "Log Out" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("fbos_access_token"))).toBeNull();

  await page.goBack();
  await expect(page).toHaveURL(/\/driver-login\?session=expired/);
});

test("customer portal invalid, expired, and authorized states are deterministic", async ({ page }) => {
  await page.goto(`/portal/load/${seed.load.id}`);
  await expect(page.getByRole("heading", { name: /secure load portal/i })).toBeVisible();

  await page.goto(`/portal/load/${seed.load.id}?token=expired-portal-token`);
  await expect(page.getByText(/portal link is expired or invalid/i)).toBeVisible();

  await page.goto(`/portal/load/${seed.load.id}?token=valid-portal-token`);
  await expect(page.getByRole("heading", { name: new RegExp(`Load ${seed.load.load_number}`) })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download packet" })).toBeVisible();
  await expect(page.getByText("Rate Confirmation")).toBeVisible();

  await page.locator('input[type="file"]').setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-pod.png"));
  await expect(page.getByText(/Document uploaded securely/i)).toBeVisible();
});
