import { expect, test } from "@playwright/test";

import { loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";
import { assertNoCriticalUiCorruption } from "../support/test-guards";

const ownerRouteChecks = [
  { path: "/dashboard", heading: /Freight Back Office OS/i },
  { path: "/dashboard/settings/carrier-profile", heading: /Carrier Profile/i },
  { path: "/dashboard/loads", heading: /Loads/i },
  { path: "/dashboard/documents", heading: /Documents/i },
  { path: "/dashboard/billing/invoices", heading: /Invoices/i },
  { path: "/dashboard/analytics", heading: /Analytics & Reporting/i },
  { path: "/dashboard/command-center", heading: /Dispatcher Command Center/i },
  { path: "/dashboard/accounting", heading: /Accounting exports and QuickBooks foundation/i },
];

test("owner launch-critical dashboard routes render from deterministic mocks", async ({ page }) => {
  await mockApi(page);
  await loginAsOwner(page);

  for (const route of ownerRouteChecks) {
    await page.goto(route.path);
    await expect(page).toHaveURL(new RegExp(route.path.replace(/[/-]/g, "\\$&")));
    await expect(page.getByRole("heading", { name: route.heading })).toBeVisible();
    await assertNoCriticalUiCorruption(page);
  }
});
