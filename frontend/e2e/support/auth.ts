import { expect, Page } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { waitForDriverPortalReady, waitForProtectedRouteSettled } from "./test-guards";

type ExpectedSession = {
  email: string;
  role: string;
};

async function waitForSessionPersistence(page: Page, expected: ExpectedSession) {
  await page.waitForFunction(
    ({ expectedEmail, expectedRole }) => {
      const token = window.localStorage.getItem("fbos_access_token");
      const organizationId = window.localStorage.getItem("fbos_organization_id");
      const role = window.localStorage.getItem("fbos_user_role");
      const storedEmail = window.localStorage.getItem("fbos_user_email");
      return Boolean(
        token &&
          organizationId &&
          role === expectedRole &&
          storedEmail === expectedEmail
      );
    },
    { expectedEmail: expected.email.trim().toLowerCase(), expectedRole: expected.role }
  );
}

async function login(page: Page, path: "/login" | "/driver-login", email: string, password: string, destinationPath: RegExp, role: string) {
  await page.goto(path);
  await page.locator("input[type='email']").fill(email);
  await page.locator("input[type='password']").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(destinationPath);
  await waitForSessionPersistence(page, { email, role });
}

export async function loginAsOwner(page: Page) {
  await login(page, "/login", seed.owner.email, seed.owner.password, /\/dashboard/, seed.owner.role);
}

export async function loginAsDriver(page: Page) {
  await login(page, "/driver-login", seed.driver.email, seed.driver.password, /\/driver-portal/, seed.driver.role);
  await waitForDriverPortalReady(page);
}

export async function gotoProtectedDriverRoute(page: Page, path: string) {
  await page.goto(path);
  await waitForDriverPortalReady(page);

  if (!page.url().includes(path)) {
    await page.goto(path);
    await waitForDriverPortalReady(page);
  }

  await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  await waitForProtectedRouteSettled(page);
}
