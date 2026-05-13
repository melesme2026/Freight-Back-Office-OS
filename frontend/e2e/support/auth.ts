import { expect, Page } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { waitForDriverPortalReady, waitForProtectedRouteSettled } from "./test-guards";

type ExpectedSession = {
  email: string;
  role: string;
  organizationId?: string;
  driverId?: string;
};

async function waitForSessionPersistence(page: Page, expected: ExpectedSession) {
  await page.waitForFunction(
    ({ expectedEmail, expectedRole, expectedOrganizationId, expectedDriverId }) => {
      function decodeJwtPayload(tokenValue: string): Record<string, unknown> | null {
        const payload = tokenValue.split(".")[1];
        if (!payload) return null;

        try {
          const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
          const padded = `${normalized}${"=".repeat((4 - (normalized.length % 4)) % 4)}`;
          return JSON.parse(window.atob(padded)) as Record<string, unknown>;
        } catch {
          return null;
        }
      }

      const token = window.localStorage.getItem("fbos_access_token");
      const organizationId = window.localStorage.getItem("fbos_organization_id");
      const role = window.localStorage.getItem("fbos_user_role");
      const storedEmail = window.localStorage.getItem("fbos_user_email");
      const driverId = window.localStorage.getItem("fbos_driver_id");
      const claims = token ? decodeJwtPayload(token) : null;
      const expiresAt = typeof claims?.exp === "number" ? claims.exp : 0;

      return Boolean(
        token &&
          claims &&
          expiresAt > Date.now() / 1000 + 30 &&
          claims.email === expectedEmail &&
          claims.role === expectedRole &&
          role === expectedRole &&
          storedEmail === expectedEmail &&
          (!expectedOrganizationId || (organizationId === expectedOrganizationId && claims.organization_id === expectedOrganizationId)) &&
          (!expectedDriverId || (driverId === expectedDriverId && claims.driver_id === expectedDriverId))
      );
    },
    {
      expectedEmail: expected.email.trim().toLowerCase(),
      expectedRole: expected.role,
      expectedOrganizationId: expected.organizationId,
      expectedDriverId: expected.driverId,
    }
  );
}

async function login(page: Page, path: "/login" | "/driver-login", email: string, password: string, destinationPath: RegExp, session: ExpectedSession) {
  await page.goto(path);
  await page.locator("input[type='email']").fill(email);
  await page.locator("input[type='password']").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(destinationPath);
  await waitForSessionPersistence(page, session);
}

export async function loginAsOwner(page: Page) {
  await login(page, "/login", seed.owner.email, seed.owner.password, /\/dashboard/, {
    email: seed.owner.email,
    role: seed.owner.role,
    organizationId: seed.organizationId,
  });
}

export async function loginAsDriver(page: Page) {
  await login(page, "/driver-login", seed.driver.email, seed.driver.password, /\/driver-portal/, {
    email: seed.driver.email,
    role: seed.driver.role,
    organizationId: seed.organizationId,
    driverId: seed.driver.id,
  });
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
