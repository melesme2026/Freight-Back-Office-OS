const ACCESS_TOKEN_KEY = "fbos_access_token";
const TOKEN_TYPE_KEY = "fbos_token_type";
const ORGANIZATION_ID_KEY = "fbos_organization_id";
const USER_EMAIL_KEY = "fbos_user_email";
const USER_ROLE_KEY = "fbos_user_role";
const JWT_EXPIRY_SKEW_SECONDS = 30;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function normalizeStoredValue(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeTokenType(value: string | null | undefined): string {
  const normalized = value?.trim();
  if (!normalized) {
    return "Bearer";
  }

  return normalized.toLowerCase() === "bearer" ? "Bearer" : normalized;
}

function getStorageItem(key: string): string | null {
  if (!isBrowser()) {
    return null;
  }

  return normalizeStoredValue(window.localStorage.getItem(key));
}

function setStorageItem(key: string, value: string): void {
  if (!isBrowser()) {
    return;
  }

  const normalized = value.trim();

  if (normalized.length === 0) {
    window.localStorage.removeItem(key);
    return;
  }

  window.localStorage.setItem(key, normalized);
}

function removeStorageItem(key: string): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(key);
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");

  if (parts.length < 2) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = `${base64}${"=".repeat((4 - (base64.length % 4)) % 4)}`;
    const json = atob(padded);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload) {
    return true;
  }

  const expClaim = payload.exp;

  if (typeof expClaim !== "number") {
    return true;
  }

  const currentEpochSeconds = Date.now() / 1000;
  return expClaim <= currentEpochSeconds + JWT_EXPIRY_SKEW_SECONDS;
}

export function getAccessToken(): string | null {
  const token = getStorageItem(ACCESS_TOKEN_KEY);

  if (!token) {
    return null;
  }

  if (isTokenExpired(token)) {
    clearAuth();
    return null;
  }

  return token;
}

export function getTokenType(): string {
  return normalizeTokenType(getStorageItem(TOKEN_TYPE_KEY));
}

export function getOrganizationId(): string | null {
  return getStorageItem(ORGANIZATION_ID_KEY);
}

export function getUserEmail(): string | null {
  return getStorageItem(USER_EMAIL_KEY);
}

export function getUserRole(): string | null {
  return getStorageItem(USER_ROLE_KEY);
}

export function getAuthSession(): {
  accessToken: string | null;
  tokenType: string;
  organizationId: string | null;
  userEmail: string | null;
  userRole: string | null;
} {
  return {
    accessToken: getAccessToken(),
    tokenType: getTokenType(),
    organizationId: getOrganizationId(),
    userEmail: getUserEmail(),
    userRole: getUserRole(),
  };
}

export function setAccessToken(token: string): void {
  setStorageItem(ACCESS_TOKEN_KEY, token);
}

export function setTokenType(tokenType: string): void {
  setStorageItem(TOKEN_TYPE_KEY, normalizeTokenType(tokenType));
}

export function setOrganizationId(organizationId: string): void {
  setStorageItem(ORGANIZATION_ID_KEY, organizationId);
}

export function setUserEmail(email: string): void {
  setStorageItem(USER_EMAIL_KEY, email);
}

export function setUserRole(role: string): void {
  setStorageItem(USER_ROLE_KEY, role);
}

export function setAuthSession(params: {
  accessToken?: string | null;
  tokenType?: string | null;
  organizationId?: string | null;
  userEmail?: string | null;
  userRole?: string | null;
}): void {
  if (params.accessToken !== undefined) {
    if (params.accessToken === null) {
      removeStorageItem(ACCESS_TOKEN_KEY);
    } else {
      setStorageItem(ACCESS_TOKEN_KEY, params.accessToken);
    }
  }

  if (params.tokenType !== undefined) {
    if (params.tokenType === null) {
      removeStorageItem(TOKEN_TYPE_KEY);
    } else {
      setStorageItem(TOKEN_TYPE_KEY, normalizeTokenType(params.tokenType));
    }
  }

  if (params.organizationId !== undefined) {
    if (params.organizationId === null) {
      removeStorageItem(ORGANIZATION_ID_KEY);
    } else {
      setStorageItem(ORGANIZATION_ID_KEY, params.organizationId);
    }
  }

  if (params.userEmail !== undefined) {
    if (params.userEmail === null) {
      removeStorageItem(USER_EMAIL_KEY);
    } else {
      setStorageItem(USER_EMAIL_KEY, params.userEmail);
    }
  }

  if (params.userRole !== undefined) {
    if (params.userRole === null) {
      removeStorageItem(USER_ROLE_KEY);
    } else {
      setStorageItem(USER_ROLE_KEY, params.userRole);
    }
  }
}

export function clearAuth(): void {
  if (!isBrowser()) {
    return;
  }

  removeStorageItem(ACCESS_TOKEN_KEY);
  removeStorageItem(TOKEN_TYPE_KEY);
  removeStorageItem(ORGANIZATION_ID_KEY);
  removeStorageItem(USER_EMAIL_KEY);
  removeStorageItem(USER_ROLE_KEY);
}

export function clearAccessToken(): void {
  removeStorageItem(ACCESS_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken() && getOrganizationId());
}
