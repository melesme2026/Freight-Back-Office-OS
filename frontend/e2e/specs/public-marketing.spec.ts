import { expect, test } from "@playwright/test";

import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("public pages and core nav route correctly", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Run freight operations/i })).toBeVisible();

  await page.getByRole("link", { name: "View Pricing" }).click();
  await expect(page).toHaveURL(/\/pricing/);
  await expect(page.getByRole("heading", { name: /Back-office plans/i })).toBeVisible();
  await expect(page.getByText("Starter")).toBeVisible();
  await expect(page.getByText("Growth")).toBeVisible();
  await expect(page.getByText("Enterprise")).toBeVisible();

  await page.getByRole("link", { name: "Request Demo" }).click();
  await expect(page).toHaveURL(/\/request-demo/);
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
