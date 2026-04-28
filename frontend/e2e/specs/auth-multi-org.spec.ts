import { test, expect } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { mockApi } from "../support/mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("staff login redirects to dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").fill(seed.owner.email);
  await page.locator("input[type='password']").fill(seed.owner.password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/dashboard/);
});

test("driver login redirects to driver portal", async ({ page }) => {
  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill(seed.driver.email);
  await page.locator("input[type='password']").fill(seed.driver.password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/driver-portal/);
});

test("role mismatch messaging is friendly", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").fill(seed.driver.email);
  await page.locator("input[type='password']").fill(seed.driver.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Use Driver Login", { exact: true })).toBeVisible();

  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill(seed.owner.email);
  await page.locator("input[type='password']").fill(seed.owner.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Use Staff Login")).toBeVisible();
});

test("staff login shows friendly invalid credentials and no raw 422 text", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").fill("owner.e2e@example.com");
  await page.locator("input[type='password']").fill("bad-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Invalid credentials")).toBeVisible();
  await expect(page.getByText("API request failed")).toHaveCount(0);
  await expect(page.getByText("422")).toHaveCount(0);
  await expect(page.getByText("organization_id")).toHaveCount(0);
});
