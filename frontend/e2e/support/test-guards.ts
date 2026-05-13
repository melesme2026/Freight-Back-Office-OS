import { expect, Page } from "@playwright/test";

export function attachRuntimeGuards(page: Page) {
  const jsErrors: string[] = [];
  const consoleErrors: string[] = [];
  const serverErrors: string[] = [];

  page.on("pageerror", (error) => jsErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      serverErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  return async () => {
    expect(jsErrors, `Unexpected page errors: ${jsErrors.join(" | ")}`).toEqual([]);
    expect(
      consoleErrors.filter(
        (entry) =>
          !entry.includes("favicon") &&
          !entry.includes("Cross origin request detected") &&
          !entry.includes("127.0.0.1") &&
          !entry.includes("/_next/")
      ),
      `Unexpected console errors: ${consoleErrors.join(" | ")}`
    ).toEqual([]);
    expect(serverErrors, `Unexpected 5xx responses: ${serverErrors.join(" | ")}`).toEqual([]);
  };
}

export async function assertNoCriticalUiCorruption(page: Page) {
  await expect(page.locator("body")).not.toContainText("undefined");
  await expect(page.locator("body")).not.toContainText("NaN");
  await expect(page.locator("body")).not.toContainText("Application error");
}

export async function waitForProtectedRouteSettled(page: Page) {
  const driverPortalSections = page.getByRole("navigation", { name: "Driver portal sections", exact: true });
  const checkingSession = page.getByText("Checking session...", { exact: true });
  const redirecting = page.getByText("Redirecting...", { exact: true });

  await expect
    .poll(async () => {
      if (await driverPortalSections.isVisible().catch(() => false)) {
        return true;
      }

      const [checkingCount, redirectingCount] = await Promise.all([
        checkingSession.count(),
        redirecting.count(),
      ]);
      return checkingCount === 0 && redirectingCount === 0;
    })
    .toBe(true);
}

export async function waitForDriverPortalReady(page: Page) {
  await waitForProtectedRouteSettled(page);

  const banner = page.getByRole("banner");
  await expect(banner.getByText("Driver Portal", { exact: true })).toBeVisible();
  await expect(banner.getByText("driver.e2e@example.com", { exact: true })).toBeVisible();

  const nav = page.getByRole("navigation", { name: "Driver portal sections", exact: true });
  await expect(nav).toBeVisible();
  await expect(nav.getByRole("link", { name: "Loads", exact: true })).toBeVisible();
}
