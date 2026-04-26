import path from "node:path";

import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { mockApi } from "../support/mock-api";
import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("owner/admin launch workflow including docs, invoice, packet, payments, and money dashboard", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await mockApi(page);

  await page.goto("/login");
  await page.locator("input[type='email']").fill(seed.owner.email);
  await page.locator("input[type='password']").fill(seed.owner.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/dashboard/onboarding");
  await expect(page.getByRole("heading", { name: /Onboarding/i })).toBeVisible();
  await page.goto("/dashboard/settings/carrier-profile");
  await expect(page.getByText(/Carrier Profile|carrier/i)).toBeVisible();
  await page.goto("/dashboard/drivers");
  await expect(page.getByRole("heading", { name: /Drivers/i })).toBeVisible();
  await page.goto("/dashboard/brokers");
  await expect(page.getByRole("heading", { name: /Brokers/i })).toBeVisible();
  await page.goto("/dashboard/customers");
  await expect(page.getByRole("heading", { name: /Customers/i })).toBeVisible();

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page.getByText(seed.load.load_number)).toBeVisible();

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-ratecon.pdf"));
  await expect(page.getByText(/uploaded successfully/i)).toBeVisible();

  await page.getByRole("button", { name: "Generate Invoice" }).click();
  await expect(page.getByText(/invoice/i).first()).toBeVisible();

  await page.getByRole("button", { name: /Generate Invoice/i }).click();
  await expect(page.locator("text=INV-E2E-001")).toHaveCount(1);

  await page.getByRole("button", { name: /Create Submission Packet/i }).click();
  await expect(page.getByRole("button", { name: /Download Packet ZIP/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Copy Submission Email/i })).toBeVisible();

  await page.getByRole("button", { name: /Send Email/i }).click();
  await expect(page.getByText(/Email sending is not enabled/i)).toBeVisible();

  await page.getByRole("button", { name: /Record partial payment/i }).click();
  await page.getByRole("button", { name: /Save payment/i }).click();
  await page.getByRole("button", { name: /Record full payment/i }).click();
  await page.getByRole("button", { name: /Save payment/i }).click();

  await page.goto("/dashboard/money");
  await expect(page.getByRole("heading", { name: "Money Dashboard" })).toBeVisible();
  await assertNoCriticalUiCorruption(page);
  await assertClean();
});
