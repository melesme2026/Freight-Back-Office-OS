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

function parseBillingMode(value: string | undefined): "pilot" | "live" {
  const normalized = normalizeOptionalText(value).toLowerCase();
  return normalized === "live" ? "live" : "pilot";
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

const publicSignupEnabled = (() => {
  const raw = normalizeOptionalText(process.env.NEXT_PUBLIC_PUBLIC_SIGNUP_ENABLED).toLowerCase();
  if (!raw) {
    return true;
  }
  return ["1", "true", "yes", "on"].includes(raw);
})();

const normalizedApiVersionPrefix = (() => {
  const source = rawApiVersionPrefix.length > 0 ? rawApiVersionPrefix : "/api/v1";
  const trimmed = trimLeadingAndTrailingSlashes(source);
  return trimmed.length > 0 ? `/${trimmed}` : "";
})();

const billingMode = parseBillingMode(process.env.NEXT_PUBLIC_BILLING_MODE);

export const appConfig = {
  appName: "Freight Back Office OS",
  apiBaseUrl: normalizedApiBaseUrl,
  apiVersionPrefix: normalizedApiVersionPrefix,
  defaultOrganizationId:
    normalizeOptionalText(process.env.NEXT_PUBLIC_ORGANIZATION_ID) ||
    "00000000-0000-0000-0000-000000000001",
  auth: {
    publicSignupEnabled,
  },
  billing: {
    mode: billingMode,
  },
  pricing: {
    starterLink:
      normalizeOptionalText(process.env.NEXT_PUBLIC_STRIPE_STARTER_LINK),
    growthLink:
      normalizeOptionalText(process.env.NEXT_PUBLIC_STRIPE_GROWTH_LINK),
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

  const baseAlreadyIncludesVersionPrefix =
    appConfig.apiBaseUrl.length > 0 &&
    appConfig.apiVersionPrefix.length > 0 &&
    (appConfig.apiBaseUrl === appConfig.apiVersionPrefix ||
      appConfig.apiBaseUrl.endsWith(appConfig.apiVersionPrefix));

  return appConfig.apiBaseUrl
    ? baseAlreadyIncludesVersionPrefix
      ? `${appConfig.apiBaseUrl}${normalizedPath}`
      : `${appConfig.apiBaseUrl}${appConfig.apiVersionPrefix}${normalizedPath}`
    : `${appConfig.apiVersionPrefix}${normalizedPath}`;
}
