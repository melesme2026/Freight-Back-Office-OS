import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const webServerCommand = process.env.PLAYWRIGHT_WEB_SERVER_COMMAND ?? "npm run build && npm run start";

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: true,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  outputDir: "test-results",
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  webServer: {
    command: webServerCommand,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    cwd: __dirname,
    timeout: 300_000,
    env: {
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
      NEXT_PUBLIC_API_VERSION_PREFIX: process.env.NEXT_PUBLIC_API_VERSION_PREFIX ?? "/api/v1",
      NEXT_PUBLIC_BILLING_MODE: process.env.NEXT_PUBLIC_BILLING_MODE ?? "pilot",
      NEXT_PUBLIC_PUBLIC_SIGNUP_ENABLED: process.env.NEXT_PUBLIC_PUBLIC_SIGNUP_ENABLED ?? "true",
    },
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
  ],
});
