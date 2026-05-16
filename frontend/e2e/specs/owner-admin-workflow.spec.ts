import path from "node:path";

import { expect, test } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";
import { assertNoCriticalUiCorruption, attachRuntimeGuards } from "../support/test-guards";

test("owner/admin launch workflow including docs, invoice, packet, payments, and money dashboard", async ({ page }) => {
  const assertClean = attachRuntimeGuards(page);
  await mockApi(page);

  await loginAsOwner(page);

  await page.goto("/dashboard/onboarding");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Onboarding Checklist$/i })).toBeVisible();
  await page.goto("/dashboard/settings/carrier-profile");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Carrier Profile$/i })).toBeVisible();
  await page.goto("/dashboard/drivers");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Drivers$/ })).toBeVisible();
  await page.goto("/dashboard/brokers");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Brokers$/ })).toBeVisible();
  await page.goto("/dashboard/customers");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Customers$/ })).toBeVisible();

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page.getByText(seed.load.load_number)).toBeVisible();

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(path.join(process.cwd(), "e2e/fixtures/files/sample-ratecon.pdf"));
  await expect(page.getByText(/upload successful/i)).toBeVisible();

  await page.getByRole("button", { name: "Generate Invoice" }).click();
  await expect(page.getByRole("button", { name: "View Invoice" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download Invoice" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Generate Invoice/i })).toHaveCount(0);

  await page.getByRole("button", { name: "View Invoice" }).click();
  await expect(page.locator("text=INV-E2E-001")).toHaveCount(1);

  await page.getByRole("button", { name: /Create Submission Packet/i }).click();
  await expect(page.getByRole("button", { name: /Download Packet ZIP/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Copy Submission Email/i })).toBeVisible();

  await page.getByRole("button", { name: "Email Packet" }).click();
  await expect(page.getByRole("heading", { name: "Email Billing Packet" })).toBeVisible();
  await page.getByLabel("Recipient email").fill("broker.e2e@example.com");
  await page.getByRole("button", { name: "Send Email" }).click();
  const packetEmailStatus = page.getByRole("status").filter({ hasText: /Packet email sent and logged/i });
  await expect(packetEmailStatus).toHaveCount(1);
  await expect(packetEmailStatus.first()).toBeVisible();

  await page.getByRole("button", { name: /Record partial payment/i }).click();
  await page.getByRole("button", { name: /Save payment/i }).click();
  await page.getByRole("button", { name: /Record full payment/i }).click();
  await page.getByRole("button", { name: /Save payment/i }).click();

  await page.goto("/dashboard/money");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Money$/ })).toBeVisible();
  await assertNoCriticalUiCorruption(page);
  await assertClean();
});
