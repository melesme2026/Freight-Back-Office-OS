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
      consoleErrors.filter((entry) => !entry.includes("favicon")),
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
