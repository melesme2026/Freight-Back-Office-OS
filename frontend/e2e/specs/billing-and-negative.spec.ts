import { expect, test } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test("billing/pricing safety copy + invalid login", async ({ page }) => {
  await mockApi(page);
  await page.goto("/pricing");
  await expect(page.getByText(/Subscription billing is not fully enabled/i)).toBeVisible();
  await expect(page.getByText(/setup required/i).first()).toBeVisible();

  await page.goto("/login");
  await page.locator("input[type='email']").fill("wrong@example.com");
  await page.locator("input[type='password']").fill("wrong-pass");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/Invalid credentials/i)).toBeVisible();

  await page.goto("/dashboard/billing");
  await expect(page).toHaveURL(/\/login/);
});
