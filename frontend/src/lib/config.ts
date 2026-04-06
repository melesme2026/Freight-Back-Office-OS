function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

function trimLeadingAndTrailingSlashes(value: string): string {
  return value.replace(/^\/+/, "").replace(/\/+$/, "");
}

const rawApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const rawApiVersionPrefix = process.env.NEXT_PUBLIC_API_VERSION_PREFIX?.trim();

const normalizedApiBaseUrl = (() => {
  if (!rawApiBaseUrl || rawApiBaseUrl.length === 0) {
    return "";
  }

  return trimTrailingSlashes(rawApiBaseUrl);
})();

const normalizedApiVersionPrefix = (() => {
  const source =
    rawApiVersionPrefix && rawApiVersionPrefix.length > 0
      ? rawApiVersionPrefix
      : "/api/v1";

  const trimmed = trimLeadingAndTrailingSlashes(source);
  return trimmed.length > 0 ? `/${trimmed}` : "";
})();

export const appConfig = {
  appName: "Freight Back Office OS",
  apiBaseUrl: normalizedApiBaseUrl,
  apiVersionPrefix: normalizedApiVersionPrefix,
  defaultOrganizationId:
    process.env.NEXT_PUBLIC_ORGANIZATION_ID ||
    "00000000-0000-0000-0000-000000000001",
};

export function buildApiUrl(path: string): string {
  const trimmedPath = path.trim();

  if (trimmedPath.length === 0) {
    return appConfig.apiBaseUrl
      ? `${appConfig.apiBaseUrl}${appConfig.apiVersionPrefix}`
      : `${appConfig.apiVersionPrefix}`;
  }

  if (/^https?:\/\//i.test(trimmedPath)) {
    return trimmedPath;
  }

  const normalizedPath = trimmedPath.startsWith("/") ? trimmedPath : `/${trimmedPath}`;

  if (normalizedPath.startsWith("/api/")) {
    return appConfig.apiBaseUrl
      ? `${appConfig.apiBaseUrl}${normalizedPath}`
      : normalizedPath;
  }

  return appConfig.apiBaseUrl
    ? `${appConfig.apiBaseUrl}${appConfig.apiVersionPrefix}${normalizedPath}`
    : `${appConfig.apiVersionPrefix}${normalizedPath}`;
}