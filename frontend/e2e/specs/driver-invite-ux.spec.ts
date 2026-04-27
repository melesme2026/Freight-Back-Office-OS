import { expect, test } from "@playwright/test";

import { loginAsOwner } from "../support/auth";
import { seed } from "../fixtures/test-data";
import { mockApi } from "../support/mock-api";

test("driver invite with disabled email shows one clean notice and copy/open actions", async ({ page }) => {
  await mockApi(page);
  await loginAsOwner(page);

  await page.goto(`/dashboard/drivers/${seed.driver.id}`);
  await page.getByRole("button", { name: "Generate driver activation invite" }).click();

  await expect(page.getByText("Email delivery is disabled. Copy the activation link and send it manually.")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Copy activation link" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open activation page" })).toBeVisible();
  await expect(page.getByText("manual-token-e2e")).toHaveCount(0);
});
