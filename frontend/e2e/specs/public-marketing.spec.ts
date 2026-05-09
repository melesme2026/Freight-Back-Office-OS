import { expect, test } from "@playwright/test";

import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("public pages, pricing, request-demo validation, and core nav route correctly", async ({ page }) => {
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

  await page.getByRole("button", { name: /submit demo request/i }).click();
  await expect(page.getByPlaceholder("Full name")).toBeFocused();
  await expect.poll(() => page.locator("form").evaluate((form) => (form as HTMLFormElement).checkValidity())).toBe(false);

  await page.route("**/api/v1/demo-requests", async (route) => {
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ data: { id: "demo-id", status: "received", message: "Demo request received." } }) });
  });
  await page.getByPlaceholder("Full name").fill("Jane Demo");
  await page.getByPlaceholder("Work email").fill("jane@example.com");
  await page.getByPlaceholder("Company").fill("Acme");
  await page.getByRole("button", { name: /submit demo request/i }).click();
  await expect(page.getByText("Demo request received. We’ll contact you shortly.")).toBeVisible();
  await expect(page.getByText(/email draft was opened/i)).toHaveCount(0);

  await page.goto("/");
  await page.getByRole("link", { name: "Staff Login" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/");
  await page.getByRole("link", { name: "Driver Login" }).click();
  await expect(page).toHaveURL(/\/driver-login/);

  await assertNoCriticalUiCorruption(page);
  await assertClean();
});
