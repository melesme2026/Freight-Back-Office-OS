import { expect, test } from "@playwright/test";

import { mockApi } from "../support/mock-api";

test("signup gating and validation copy", async ({ page }) => {
  await mockApi(page);
  await page.goto("/signup");

  if (await page.getByText("Public owner signup is currently disabled.").isVisible()) {
    await expect(page.getByRole("link", { name: "Request Access" })).toBeVisible();
  } else {
    await expect(page.getByText("Staff and drivers are invite-only")).toBeVisible();
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("All fields are required.")).toBeVisible();

    await page.getByPlaceholder("Full name").fill("Owner E2E");
    await page.getByPlaceholder("Company / organization").fill("Duplicate Org");
    await page.getByPlaceholder("Work email").fill("owner.e2e@example.com");
    await page.getByPlaceholder("Password (min 8 chars)").fill("Password123!");
    await page.getByPlaceholder("Confirm password").fill("Password123!");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText(/Organization already exists/i)).toBeVisible();
  }
});
