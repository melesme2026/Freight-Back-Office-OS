import { buildApiUrl } from "@/lib/config";

type RequestOptions = RequestInit & {
  token?: string;
  organizationId?: string;
};

const DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001";

function getStoredAccessToken(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const value = window.localStorage.getItem("access_token");
  return value || undefined;
}

function getStoredOrganizationId(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const value = window.localStorage.getItem("organization_id");
  return value || undefined;
}

function normalizeHeaders(headers?: HeadersInit): Record<string, string> {
  if (!headers) {
    return {};
  }

  if (headers instanceof Headers) {
    return Object.fromEntries(headers.entries());
  }

  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }

  return { ...headers };
}

async function parseResponseBody<T>(response: Response): Promise<T> {
  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.toLowerCase().includes("application/json")) {
    return response.json() as Promise<T>;
  }

  const text = await response.text();
  return text as T;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, organizationId, headers, body, ...rest } = options;

  const resolvedToken = token ?? getStoredAccessToken();
  const resolvedOrganizationId =
    organizationId ?? getStoredOrganizationId() ?? DEFAULT_ORGANIZATION_ID;

  const normalizedHeaders = normalizeHeaders(headers);
  const hasBody = body !== undefined && body !== null;

  const response = await fetch(buildApiUrl(path), {
    ...rest,
    body,
    headers: {
      Accept: "application/json",
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...(resolvedToken ? { Authorization: `Bearer ${resolvedToken}` } : {}),
      ...(resolvedOrganizationId ? { "X-Organization-Id": resolvedOrganizationId } : {}),
      ...normalizedHeaders,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let errorMessage = `API request failed (${response.status})`;

    try {
      const errorBody = (await response.json()) as {
        error?: { message?: string };
        detail?: string | Array<unknown>;
        message?: string;
      };

      if (errorBody?.error?.message) {
        errorMessage = `${errorMessage}: ${errorBody.error.message}`;
      } else if (typeof errorBody?.detail === "string") {
        errorMessage = `${errorMessage}: ${errorBody.detail}`;
      } else if (errorBody?.detail) {
        errorMessage = `${errorMessage}: ${JSON.stringify(errorBody.detail)}`;
      } else if (typeof errorBody?.message === "string" && errorBody.message.trim().length > 0) {
        errorMessage = `${errorMessage}: ${errorBody.message}`;
      }
    } catch {
      const text = await response.text();
      if (text) {
        errorMessage = `${errorMessage}: ${text}`;
      }
    }

    throw new Error(errorMessage);
  }

  return parseResponseBody<T>(response);
}

export const apiClient = {
  get: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "DELETE" }),
};