import { test, expect } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("staff login supports workspace selection for multi-org accounts", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").fill("multi@example.com");
  await page.locator("input[type='password']").fill("Owner123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Select workspace")).toBeVisible();
  await expect(page.getByText("This email is linked to multiple workspaces. Choose which workspace to access.")).toBeVisible();
  await page.getByRole("button", { name: "Adwa Express LLC" }).click();

  await expect(page).toHaveURL(/\/dashboard/);
});

test("driver login supports workspace selection for multi-org accounts", async ({ page }) => {
  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill("multi@example.com");
  await page.locator("input[type='password']").fill("Owner123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Select workspace")).toBeVisible();
  await expect(page.getByText("This email is linked to multiple workspaces. Choose which workspace to access.")).toBeVisible();
  await page.getByRole("button", { name: "Adwa Driver Ops" }).click();

  await expect(page).toHaveURL(/\/driver-portal/);
});

test("driver login shows friendly guidance for non-driver workspace", async ({ page }) => {
  await page.goto("/driver-login");
  await page.locator("input[type='email']").fill("multi@example.com");
  await page.locator("input[type='password']").fill("Owner123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.getByRole("button", { name: "Adwa Express LLC" }).click();
  await expect(page.getByText("This workspace is not a driver account. Use Staff Login.")).toBeVisible();
});

test("staff login shows friendly invalid credentials and no raw 422 text", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").fill("owner.e2e@example.com");
  await page.locator("input[type='password']").fill("bad-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await expect(page.getByText("API request failed")).toHaveCount(0);
  await expect(page.getByText("422")).toHaveCount(0);
  await expect(page.getByText("organization_id")).toHaveCount(0);
});
