import { expect, test, type Page } from "@playwright/test";

import { seed } from "../fixtures/test-data";
import { gotoProtectedDriverRoute, loginAsDriver, loginAsOwner } from "../support/auth";
import { mockApi } from "../support/mock-api";

async function expectNoPageOverflow(page: Page) {
  await expect(
    page.locator("body").evaluate((node) => node.scrollWidth <= window.innerWidth + 1)
  ).resolves.toBeTruthy();
}

test("mobile smoke: landing and driver load detail actions visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);

  await page.goto("/");
  await expect(page.getByRole("link", { name: "Request a demo" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See the workflow" })).toBeVisible();
  await expectNoPageOverflow(page);

  await loginAsDriver(page);
  await gotoProtectedDriverRoute(page, `/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByRole("main").getByRole("heading", { name: new RegExp(`^Load ${seed.load.load_number}$`) })).toBeVisible();
  await expect(page.getByRole("region", { name: "Document Uploads" })).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: owner dashboard, loads, and load detail do not page-overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockApi(page);

  await loginAsOwner(page);
  await expect(page.getByRole("navigation").getByRole("link", { name: "Loads" })).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto("/dashboard/loads");
  await expect(page.getByRole("main").getByRole("heading", { name: /^Loads$/ })).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto(`/dashboard/loads/${seed.load.id}`);
  await expect(page.getByRole("main").getByRole("heading", { name: seed.load.load_number })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: driver portal overview and uploads remain touch-friendly", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await mockApi(page);

  await loginAsDriver(page);
  await expect(page.getByRole("heading", { name: "Driver Workspace" })).toBeVisible();
  await expectNoPageOverflow(page);

  await gotoProtectedDriverRoute(page, "/driver-portal/uploads");
  await expect(page.getByRole("heading", { name: /Upload Documents/ })).toBeVisible();
  await expect(page.getByLabel("File or photo", { exact: true })).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: PWA shell, push preferences, and ETA workflow are available", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);

  await page.goto("/manifest.webmanifest");
  await expect(page.locator("body")).toContainText("ADWA Freight Driver");

  await loginAsDriver(page);
  await gotoProtectedDriverRoute(page, `/driver-portal/loads/${seed.load.id}`);
  await expect(page.getByText("Online and ready to sync")).toBeVisible();
  await expect(page.getByText("Push reminders")).toBeVisible();
  await expect(page.getByRole("heading", { name: "ETA / check-in" })).toBeVisible();
  await page.getByLabel("ETA note").fill("Arriving 3:30 PM after shipper delay");
  await page.getByRole("button", { name: /Send in-transit/ }).click();
  await expect(page.getByText(/In-transit \/ ETA update sent to dispatch/)).toBeVisible();
  await expectNoPageOverflow(page);
});

test("mobile smoke: camera-first upload shows preview and success feedback", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);

  await loginAsDriver(page);
  await gotoProtectedDriverRoute(page, "/driver-portal/uploads");
  expect(await page.evaluate(() => window.navigator.onLine)).toBe(true);
  await expect(page.getByLabel("Assigned load", { exact: true })).toHaveValue(seed.load.id);
  await page.getByLabel("File or photo", { exact: true }).setInputFiles({
    name: "pod-photo.png",
    mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgo=", "base64"),
  });

  await expect(page.getByAltText("Selected document preview")).toBeVisible();
  const uploadResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/driver/documents/upload") &&
      response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "Upload Document" }).click();
  const uploadResponse = await uploadResponsePromise;
  const uploadBody = await uploadResponse.json();
  expect([200, 201]).toContain(uploadResponse.status());
  expect(uploadResponse.headers()["x-e2e-upload-mock"]).toBe("hit");
  expect(uploadBody).toEqual({
    data: [
      {
        original_filename: "pod-photo.png",
        filename: "pod-photo.png",
        document_type: "proof_of_delivery",
        status: "uploaded",
      },
    ],
  });
  await expect(page.getByRole("status")).toHaveText("Upload successful: pod-photo.png");
  await expectNoPageOverflow(page);
});
