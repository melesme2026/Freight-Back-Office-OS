import { expect, test } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test("pricing page hides developer setup copy in pilot mode", async ({ page }) => {
  await mockApi(page);
  await page.goto("/pricing");

  await expect(page.getByText(/Pilot access: start using the platform now/i)).toBeVisible();
  await expect(page.getByRole("link", { name: "Start using now" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Request onboarding" })).toBeVisible();

  await expect(page.getByText(/Setup required/i)).toHaveCount(0);
  await expect(page.getByText(/checkout link is not configured/i)).toHaveCount(0);
  await expect(page.getByText(/Subscription billing is not fully enabled yet/i)).toHaveCount(0);
});

test("billing dashboard shows safe pilot billing state", async ({ page }) => {
  await mockApi(page);

  await page.goto("/login");
  await page.locator("input[type='email']").fill("wrong@example.com");
  await page.locator("input[type='password']").fill("wrong-pass");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/Invalid credentials/i)).toBeVisible();

  await page.goto("/dashboard/billing");
  await expect(page).toHaveURL(/\/login/);
});
