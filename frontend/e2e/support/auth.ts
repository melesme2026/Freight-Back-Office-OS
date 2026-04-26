import { expect, Page } from "@playwright/test";

import { seed } from "../fixtures/test-data";

async function login(page: Page, path: "/login" | "/driver-login", email: string, password: string, destinationPath: RegExp) {
  await page.goto(path);
  await page.locator("input[type='email']").fill(email);
  await page.locator("input[type='password']").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(destinationPath);
}

export async function loginAsOwner(page: Page) {
  await login(page, "/login", seed.owner.email, seed.owner.password, /\/dashboard/);
}

export async function loginAsDriver(page: Page) {
  await login(page, "/driver-login", seed.driver.email, seed.driver.password, /\/driver-portal/);
}
