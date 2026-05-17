import { expect, test, type Page } from "@playwright/test";

import { loginAsDriver, loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";

async function expectNoPageOverflow(page: Page) {
  await expect(page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth + 1)).resolves.toBeTruthy();
}

test("owner workspace uses grouped role-ready navigation and active highlighting", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 950 });
  await mockApi(page);
  await loginAsOwner(page);

  const nav = page.getByRole("navigation", { name: "Workspace sections" });
  await expect(nav.getByRole("button", { name: /Operations/ })).toBeVisible();
  await expect(nav.getByRole("button", { name: /Finance/ })).toBeVisible();
  await expect(nav.getByRole("button", { name: /Relationships/ })).toBeVisible();
  await expect(nav.getByRole("button", { name: /Intelligence/ })).toBeVisible();
  await expect(nav.getByRole("button", { name: /Administration/ })).toBeVisible();
  await expect(nav.getByRole("link", { name: /Operational Insights/ })).toBeVisible();
  await expect(nav.getByRole("link", { name: /Overview/ })).toHaveAttribute("aria-current", "page");

  await page.goto("/dashboard/billing");
  await expect(nav.getByRole("link", { name: /Billing/ })).toHaveAttribute("aria-current", "page");
  await expectNoPageOverflow(page);
});

test("mobile workspace drawer opens, collapses sections, and closes on navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await loginAsOwner(page);

  await page.getByRole("button", { name: "Menu" }).click();
  const dialog = page.getByRole("dialog", { name: "Workspace navigation" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("link", { name: /Loads/ })).toBeVisible();

  await dialog.getByRole("button", { name: /Finance/ }).click();
  await expect(dialog.getByRole("link", { name: /Billing/ })).toBeHidden();
  await dialog.getByRole("button", { name: /Finance/ }).click();
  await dialog.getByRole("link", { name: /Billing/ }).click();
  await expect(page).toHaveURL(/\/dashboard\/billing/);
  await expect(dialog).toBeHidden();
  await expectNoPageOverflow(page);
});

test("overview prioritizes operational KPIs, priorities, empty guidance, skeleton-safe layout, and quick actions", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await mockApi(page);
  await loginAsOwner(page);

  const primaryKpis = page.getByRole("heading", { name: "Primary operational KPIs" });
  await expect(primaryKpis).toBeVisible();
  await expect(page.getByText("Missing Documents")).toBeVisible();
  await expect(page.getByText("Ready to Invoice")).toBeVisible();
  await expect(page.getByText("Awaiting Submission")).toBeVisible();
  await expect(page.getByText("Payment Overdue")).toBeVisible();
  await expect(page.getByText("Open Follow-Ups")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Active priorities" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Secondary intelligence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quick access workspaces" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Documents/ })).toBeVisible();
  await expect(page.getByText(/Loading operational summaries|Loading priorities|Loading\.\.\./)).toHaveCount(0);
  await expectNoPageOverflow(page);
});

test("driver portal keeps mobile tabs usable and emphasizes next required action", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await mockApi(page);
  await loginAsDriver(page);

  const nav = page.getByRole("navigation", { name: "Driver portal sections" });
  await expect(nav.getByRole("link", { name: /Overview/ })).toHaveAttribute("aria-current", "page");
  await expect(nav.getByRole("link", { name: /Loads/ })).toBeVisible();
  await expect(nav.getByRole("link", { name: /Uploads/ })).toBeVisible();
  await expect(nav.getByRole("link", { name: /Support/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Active Load" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Next Required Action" })).toBeVisible();
  await expect(page.getByText("Upload progression")).toBeVisible();
  await expectNoPageOverflow(page);
});
