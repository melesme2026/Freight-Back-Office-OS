function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

function trimLeadingAndTrailingSlashes(value: string): string {
  return value.replace(/^\/+/, "").replace(/\/+$/, "");
}

function normalizeOptionalText(value: string | undefined): string {
  return value?.trim() ?? "";
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

const rawApiBaseUrl = normalizeOptionalText(process.env.NEXT_PUBLIC_API_BASE_URL);
const rawApiVersionPrefix = normalizeOptionalText(
  process.env.NEXT_PUBLIC_API_VERSION_PREFIX
);

const normalizedApiBaseUrl = (() => {
  if (rawApiBaseUrl.length === 0) {
    return "";
  }

  return trimTrailingSlashes(rawApiBaseUrl);
})();

const normalizedApiVersionPrefix = (() => {
  const source = rawApiVersionPrefix.length > 0 ? rawApiVersionPrefix : "/api/v1";
  const trimmed = trimLeadingAndTrailingSlashes(source);
  return trimmed.length > 0 ? `/${trimmed}` : "";
})();

export const appConfig = {
  appName: "Freight Back Office OS",
  apiBaseUrl: normalizedApiBaseUrl,
  apiVersionPrefix: normalizedApiVersionPrefix,
  defaultOrganizationId:
    normalizeOptionalText(process.env.NEXT_PUBLIC_ORGANIZATION_ID) ||
    "00000000-0000-0000-0000-000000000001",
  pricing: {
    starterLink:
      normalizeOptionalText(process.env.NEXT_PUBLIC_STRIPE_STARTER_LINK) ||
      "https://buy.stripe.com/fZu8wP1HIc6m48R0PA7Vm00",
    growthLink:
      normalizeOptionalText(process.env.NEXT_PUBLIC_STRIPE_GROWTH_LINK) ||
      "https://buy.stripe.com/fZu7sL1HI7Q6fRz7dY7Vm01",
    enterpriseContact:
      normalizeOptionalText(process.env.NEXT_PUBLIC_ENTERPRISE_CONTACT) ||
      "/request-demo",
  },
};

export function buildApiUrl(path: string): string {
  const trimmedPath = path.trim();

  if (trimmedPath.length === 0) {
    return appConfig.apiBaseUrl
      ? `${appConfig.apiBaseUrl}${appConfig.apiVersionPrefix}`
      : `${appConfig.apiVersionPrefix}`;
  }

  if (isAbsoluteUrl(trimmedPath)) {
    return trimmedPath;
  }

  const normalizedPath = trimmedPath.startsWith("/")
    ? trimmedPath
    : `/${trimmedPath}`;

  if (normalizedPath.startsWith("/api/")) {
    return appConfig.apiBaseUrl
      ? `${appConfig.apiBaseUrl}${normalizedPath}`
      : normalizedPath;
  }

  return appConfig.apiBaseUrl
    ? `${appConfig.apiBaseUrl}${appConfig.apiVersionPrefix}${normalizedPath}`
    : `${appConfig.apiVersionPrefix}${normalizedPath}`;
}
