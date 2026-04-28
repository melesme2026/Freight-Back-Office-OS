import { expect, test } from "@playwright/test";

import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("public pages and core nav route correctly", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /without spreadsheets, texts, or lost paperwork/i })).toBeVisible();

  await page.getByRole("link", { name: "View Pricing" }).click();
  await expect(page).toHaveURL(/\/pricing/);
  await expect(page.getByRole("heading", { name: /Simple freight back-office plans/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Starter" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Growth" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Enterprise" })).toBeVisible();

  await Promise.all([
    page.waitForURL(/\/request-demo/),
    page.getByRole("link", { name: "Request onboarding" }).first().click(),
  ]);
  await expect(page.getByRole("heading", { name: /walkthrough/i })).toBeVisible();

  await page.goto("/");
  await page.getByRole("link", { name: "Staff Login" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/");
  await page.getByRole("link", { name: "Driver Login" }).click();
  await expect(page).toHaveURL(/\/driver-login/);

  await assertNoCriticalUiCorruption(page);
  await assertClean();
});
