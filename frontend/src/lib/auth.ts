const ACCESS_TOKEN_KEY = "fbos_access_token";
const TOKEN_TYPE_KEY = "fbos_token_type";
const ORGANIZATION_ID_KEY = "fbos_organization_id";
const USER_EMAIL_KEY = "fbos_user_email";
const USER_ROLE_KEY = "fbos_user_role";
const DRIVER_ID_KEY = "fbos_driver_id";
const JWT_EXPIRY_SKEW_SECONDS = 30;
const AUTH_CHANGED_EVENT = "fbos-auth-changed";

const AUTH_STORAGE_KEYS = [
  ACCESS_TOKEN_KEY,
  TOKEN_TYPE_KEY,
  ORGANIZATION_ID_KEY,
  USER_EMAIL_KEY,
  USER_ROLE_KEY,
  DRIVER_ID_KEY,
  "access_token",
  "token_type",
  "organization_id",
  "user_email",
  "user_role",
  "driver_id",
  "auth_token",
  "auth_user",
  "auth_session",
] as const;

type JwtPayload = Record<string, unknown>;

export type AuthSession = {
  accessToken: string | null;
  tokenType: string;
  organizationId: string | null;
  userEmail: string | null;
  userRole: string | null;
  driverId: string | null;
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function normalizeStoredValue(value: string | null | undefined): string | null {
  if (value === null || value === undefined) {
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

function emitAuthChanged(): void {
  if (!isBrowser()) {
    return;
  }

  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function onAuthChanged(listener: () => void): () => void {
  if (!isBrowser()) {
    return () => undefined;
  }

  window.addEventListener(AUTH_CHANGED_EVENT, listener);
  window.addEventListener("storage", listener);
  window.addEventListener("pageshow", listener);
  return () => {
    window.removeEventListener(AUTH_CHANGED_EVENT, listener);
    window.removeEventListener("storage", listener);
    window.removeEventListener("pageshow", listener);
  };
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split(".");

  if (parts.length !== 3) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = `${base64}${"=".repeat((4 - (base64.length % 4)) % 4)}`;
    const json = atob(padded);
    const parsed = JSON.parse(json) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as JwtPayload) : null;
  } catch {
    return null;
  }
}

function getTokenStringClaim(payload: JwtPayload, claim: string): string | null {
  const value = payload[claim];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function isTokenExpiredPayload(payload: JwtPayload): boolean {
  const expClaim = payload.exp;

  if (typeof expClaim !== "number" || !Number.isFinite(expClaim)) {
    return true;
  }

  const currentEpochSeconds = Date.now() / 1000;
  return expClaim <= currentEpochSeconds + JWT_EXPIRY_SKEW_SECONDS;
}

function deriveSessionFromToken(token: string, tokenType: string): AuthSession | null {
  const payload = decodeJwtPayload(token);
  if (!payload || isTokenExpiredPayload(payload)) {
    return null;
  }

  const organizationId = getTokenStringClaim(payload, "organization_id");
  const userRole = getTokenStringClaim(payload, "role")?.toLowerCase() ?? null;
  const userEmail = getTokenStringClaim(payload, "email") ?? getTokenStringClaim(payload, "sub");
  const driverId = getTokenStringClaim(payload, "driver_id");

  if (!organizationId || !userRole) {
    return null;
  }

  return {
    accessToken: token,
    tokenType: normalizeTokenType(tokenType),
    organizationId,
    userEmail,
    userRole,
    driverId,
  };
}

function persistDerivedSession(session: AuthSession): void {
  if (!session.accessToken) {
    clearAuth({ emit: false });
    return;
  }

  setStorageItem(ACCESS_TOKEN_KEY, session.accessToken);
  setStorageItem(TOKEN_TYPE_KEY, session.tokenType);
  setStorageItem(ORGANIZATION_ID_KEY, session.organizationId ?? "");
  setStorageItem(USER_EMAIL_KEY, session.userEmail ?? "");
  setStorageItem(USER_ROLE_KEY, session.userRole ?? "");
  if (session.driverId) {
    setStorageItem(DRIVER_ID_KEY, session.driverId);
  } else {
    removeStorageItem(DRIVER_ID_KEY);
  }
}

export function restoreAuthSession(): AuthSession {
  const token = getStorageItem(ACCESS_TOKEN_KEY);
  if (!token) {
    clearAuth({ emit: false });
    return emptySession();
  }

  const session = deriveSessionFromToken(token, getStorageItem(TOKEN_TYPE_KEY) ?? "Bearer");
  if (!session) {
    clearAuth({ emit: false });
    return emptySession();
  }

  persistDerivedSession(session);
  return session;
}

function emptySession(): AuthSession {
  return {
    accessToken: null,
    tokenType: "Bearer",
    organizationId: null,
    userEmail: null,
    userRole: null,
    driverId: null,
  };
}

export function getAccessToken(): string | null {
  return restoreAuthSession().accessToken;
}

export function getTokenType(): string {
  return restoreAuthSession().tokenType;
}

export function getOrganizationId(): string | null {
  return restoreAuthSession().organizationId;
}

export function getUserEmail(): string | null {
  return restoreAuthSession().userEmail;
}

export function getUserRole(): string | null {
  return restoreAuthSession().userRole;
}

export function getDriverId(): string | null {
  return restoreAuthSession().driverId;
}

export function getAuthSession(): AuthSession {
  return restoreAuthSession();
}

export function setAccessToken(token: string): void {
  setAuthSession({ accessToken: token });
}

export function setTokenType(tokenType: string): void {
  setStorageItem(TOKEN_TYPE_KEY, normalizeTokenType(tokenType));
  restoreAuthSession();
  emitAuthChanged();
}

export function setOrganizationId(organizationId: string): void {
  setStorageItem(ORGANIZATION_ID_KEY, organizationId);
  restoreAuthSession();
  emitAuthChanged();
}

export function setUserEmail(email: string): void {
  setStorageItem(USER_EMAIL_KEY, email);
  restoreAuthSession();
  emitAuthChanged();
}

export function setUserRole(role: string): void {
  setStorageItem(USER_ROLE_KEY, role);
  restoreAuthSession();
  emitAuthChanged();
}

export function setDriverId(driverId: string): void {
  setStorageItem(DRIVER_ID_KEY, driverId);
  restoreAuthSession();
  emitAuthChanged();
}

export function setAuthSession(params: {
  accessToken?: string | null;
  tokenType?: string | null;
  organizationId?: string | null;
  userEmail?: string | null;
  userRole?: string | null;
  driverId?: string | null;
}): void {
  if (params.accessToken === null) {
    clearAuth();
    return;
  }

  if (params.accessToken !== undefined) {
    setStorageItem(ACCESS_TOKEN_KEY, params.accessToken);
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
  if (params.driverId !== undefined) {
    if (params.driverId === null) {
      removeStorageItem(DRIVER_ID_KEY);
    } else {
      setStorageItem(DRIVER_ID_KEY, params.driverId);
    }
  }

  const session = restoreAuthSession();
  if (!session.accessToken) {
    clearAuth({ emit: false });
  }
  emitAuthChanged();
}

export function clearAuth(options: { emit?: boolean } = {}): void {
  if (!isBrowser()) {
    return;
  }

  AUTH_STORAGE_KEYS.forEach((key) => removeStorageItem(key));
  if (options.emit !== false) {
    emitAuthChanged();
  }
}

export function clearAccessToken(): void {
  clearAuth();
}

export function isAuthenticated(): boolean {
  const session = restoreAuthSession();
  return Boolean(session.accessToken && session.organizationId);
}
