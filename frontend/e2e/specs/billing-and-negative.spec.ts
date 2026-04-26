import { expect, test } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test("billing/pricing safety copy + invalid login", async ({ page }) => {
  await mockApi(page);
  await page.goto("/pricing");
  const starterCheckoutLink = page.getByRole("link", { name: "Start Starter" });
  const starterSetupRequiredLink = page.getByRole("link", { name: "Setup required" }).first();
  if (await starterCheckoutLink.count()) {
    await expect(starterCheckoutLink).toBeVisible();
    await expect(starterCheckoutLink).toHaveAttribute("href", /^https?:\/\//);
    await expect(starterCheckoutLink).toHaveAttribute("target", "_blank");
    await expect(starterCheckoutLink).toHaveAttribute("rel", /noopener/);
  } else {
    await expect(page.getByText(/Subscription billing is not fully enabled/i)).toBeVisible();
    await expect(starterSetupRequiredLink).toBeVisible();
  }

  await page.goto("/login");
  await page.locator("input[type='email']").fill("wrong@example.com");
  await page.locator("input[type='password']").fill("wrong-pass");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/Invalid credentials/i)).toBeVisible();

  await page.goto("/dashboard/billing");
  await expect(page).toHaveURL(/\/login/);
});
