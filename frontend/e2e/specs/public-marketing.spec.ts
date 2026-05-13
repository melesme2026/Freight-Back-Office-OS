import { expect, test } from "@playwright/test";

import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("public pages and core nav route correctly", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /cleaner freight back office for paperwork, billing packets, invoices, factoring, and collections/i })).toBeVisible();

  await page.getByRole("navigation", { name: "Public navigation" }).getByRole("link", { name: "Pricing", exact: true }).click();
  await expect(page).toHaveURL(/\/pricing/);
  await expect(page.getByRole("heading", { name: /Clear starting points for freight back-office teams/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Starter" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Growth" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fleet / Enterprise" })).toBeVisible();

  await Promise.all([
    page.waitForURL(/\/request-demo/),
    page.getByRole("link", { name: "Request Starter demo" }).click(),
  ]);
  await expect(page.getByRole("heading", { name: "Book a freight back-office walkthrough" })).toBeVisible();


  await page.route("**/api/v1/demo-requests", async (route) => {
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ data: { id: "demo-id", status: "received", message: "Demo request received." } }) });
  });
  await page.getByLabel("Full name").fill("Jane Demo");
  await page.getByLabel("Work email").fill("jane@example.com");
  await page.getByLabel("Company").fill("Acme");
  await page.getByRole("button", { name: /submit demo request/i }).click();
  await expect(page.getByText("Demo request received. We’ll contact you shortly.")).toBeVisible();
  await expect(page.getByText(/email draft was opened/i)).toHaveCount(0);

  await page.goto("/");
  await page.getByRole("navigation", { name: "Public navigation" }).getByRole("link", { name: "App login" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/");
  await page.getByRole("navigation", { name: "Public navigation" }).getByRole("link", { name: "Driver Login" }).click();
  await expect(page).toHaveURL(/\/driver-login/);

  await assertNoCriticalUiCorruption(page);
  await assertClean();
});
