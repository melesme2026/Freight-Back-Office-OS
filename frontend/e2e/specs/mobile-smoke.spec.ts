import { expect, test, type Page, type Request } from "@playwright/test";

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
  await expect(page.getByLabel("Upload Document Type")).toBeVisible();
  await expect(page.getByLabel("Document file or photo")).toBeVisible();
  await expect(page.getByRole("button", { name: "Choose file or photo" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload Document" })).toBeVisible();
  await expect(page.getByText("rate_confirmation.pdf")).toBeVisible();
  await expect(page.getByText("received · extraction skipped")).toBeVisible();
  await expect(page.getByText("4 KB").first()).toBeVisible();
  await expectNoPageOverflow(page);

  await page.getByLabel("Upload Document Type").selectOption("rate_confirmation");
  await page.getByLabel("Document file or photo").setInputFiles({
    name: "ratecon-mobile.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 mobile rate confirmation"),
  });
  await expect(page.getByText("Selected: ratecon-mobile.pdf")).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload Document" })).toBeVisible();
  await page.getByRole("button", { name: "Upload Document" }).click();
  await expect(page.getByRole("status")).toHaveText(/Upload successful: ratecon-mobile\.pdf \(Rate Confirmation\)\./);
  await expect(page.getByText("ratecon-mobile.pdf")).toBeVisible();
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

  const uploadRequestDiagnostics: string[] = [];
  const failedRequests: string[] = [];
  const consoleErrors: string[] = [];
  const isUploadRequest = (request: Request) => {
    const url = new URL(request.url());
    return url.pathname === "/api/v1/driver/documents/upload" && request.method() === "POST";
  };

  page.on("request", (request) => {
    if (isUploadRequest(request)) {
      uploadRequestDiagnostics.push(`request ${request.method()} ${request.url()} type=${request.resourceType()}`);
    }
  });
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    const diagnostic = `${request.method()} ${request.url()} ${failure?.errorText ?? "unknown request failure"}`;
    failedRequests.push(diagnostic);
    if (isUploadRequest(request)) uploadRequestDiagnostics.push(`requestfailed ${diagnostic}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  const uploadResponsePromise = page.waitForResponse((response) => isUploadRequest(response.request()));
  const uploadFinishedPromise = page.waitForEvent("requestfinished", isUploadRequest);
  await page.getByRole("button", { name: "Upload Document" }).click();
  const uploadResponse = await uploadResponsePromise;
  const uploadBodyText = await uploadResponse.text();
  uploadRequestDiagnostics.push(
    `response ${uploadResponse.status()} ${uploadResponse.url()} headers=${JSON.stringify(uploadResponse.headers())} body=${uploadBodyText}`
  );
  await uploadFinishedPromise;
  const uploadBody = JSON.parse(uploadBodyText) as unknown;
  expect(uploadResponse.request().resourceType()).toBe("xhr");
  expect(failedRequests, uploadRequestDiagnostics.join("\n")).toEqual([]);
  expect(consoleErrors, uploadRequestDiagnostics.join("\n")).toEqual([]);
  expect([200, 201]).toContain(uploadResponse.status());
  expect(uploadResponse.headers()["x-e2e-upload-mock"]).toBe("hit");
  expect(uploadBody).toEqual({
    data: [
      {
        id: "driver-upload-e2e-001",
        load_id: seed.load.id,
        load_number: seed.load.load_number,
        original_filename: "pod-photo.png",
        filename: "pod-photo.png",
        file_name: "pod-photo.png",
        document_type: "proof_of_delivery",
        received_status: "received",
        processing_status: "completed",
        extraction_status: "skipped",
        received_at: "2026-01-15T12:00:00.000Z",
        status: "uploaded",
      },
    ],
  });
  await expect(page.getByRole("status")).toHaveText("Upload successful: pod-photo.png");
  await expectNoPageOverflow(page);
});

test("load detail renders core content when optional sections fail", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);

  await page.route("**/api/v1/loads/*/packet-audit", async (route) => {
    await route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Packet audit timed out" } }),
    });
  });
  await page.route("**/api/v1/loads/*/submission-packets", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "Submission packets unavailable" } }),
      });
      return;
    }
    await route.fallback();
  });

  await loginAsOwner(page);
  await page.goto(`/dashboard/loads/${seed.load.id}`);

  await expect(page.getByRole("main").getByRole("heading", { name: seed.load.load_number })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(page.getByText("Packet audit timed out")).toBeVisible();
  await expect(page.getByText("Submission packets unavailable")).toBeVisible();
  await expect(page.getByLabel("Upload Document Type")).toBeVisible();
  await expectNoPageOverflow(page);
});
