import { buildApiUrl } from "@/lib/config";

type RequestOptions = Omit<RequestInit, "body"> & {
  token?: string;
  organizationId?: string;
  body?: BodyInit | null;
  jsonBody?: unknown;
  responseType?: "json" | "text" | "blob" | "response";
};

const DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001";
const ACCESS_TOKEN_STORAGE_KEY = "fbos_access_token";
const TOKEN_TYPE_STORAGE_KEY = "fbos_token_type";
const ORGANIZATION_ID_STORAGE_KEY = "fbos_organization_id";

function getStoredAccessToken(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const value = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)?.trim();
  return value && value.length > 0 ? value : undefined;
}

function getStoredTokenType(): string {
  if (typeof window === "undefined") {
    return "Bearer";
  }

  const value = window.localStorage.getItem(TOKEN_TYPE_STORAGE_KEY)?.trim();
  return value && value.length > 0 ? value : "Bearer";
}

function getStoredOrganizationId(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const value = window.localStorage.getItem(ORGANIZATION_ID_STORAGE_KEY)?.trim();
  return value && value.length > 0 ? value : undefined;
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

function isFormData(value: unknown): value is FormData {
  return typeof FormData !== "undefined" && value instanceof FormData;
}

function isBlob(value: unknown): value is Blob {
  return typeof Blob !== "undefined" && value instanceof Blob;
}

function isArrayBuffer(value: unknown): value is ArrayBuffer {
  return typeof ArrayBuffer !== "undefined" && value instanceof ArrayBuffer;
}

function resolveRequestBody(options: Pick<RequestOptions, "body" | "jsonBody">): {
  body: BodyInit | null | undefined;
  shouldSetJsonContentType: boolean;
} {
  if (options.body !== undefined) {
    return {
      body: options.body,
      shouldSetJsonContentType: false,
    };
  }

  if (options.jsonBody === undefined) {
    return {
      body: undefined,
      shouldSetJsonContentType: false,
    };
  }

  return {
    body: JSON.stringify(options.jsonBody),
    shouldSetJsonContentType: true,
  };
}

async function parseResponseBody<T>(
  response: Response,
  responseType: RequestOptions["responseType"] = "json"
): Promise<T> {
  if (responseType === "response") {
    return response as T;
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  if (responseType === "blob") {
    return (await response.blob()) as T;
  }

  if (responseType === "text") {
    return (await response.text()) as T;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.toLowerCase().includes("application/json")) {
    return response.json() as Promise<T>;
  }

  const text = await response.text();
  return text as T;
}

async function buildErrorMessage(response: Response): Promise<string> {
  let errorMessage = `API request failed (${response.status})`;

  try {
    const contentType = response.headers.get("content-type") ?? "";

    if (contentType.toLowerCase().includes("application/json")) {
      const errorBody = (await response.json()) as {
        error?: { message?: string; details?: unknown };
        detail?: string | Array<unknown> | Record<string, unknown>;
        message?: string;
      };

      if (errorBody?.error?.message) {
        return `${errorMessage}: ${errorBody.error.message}`;
      }

      if (typeof errorBody?.detail === "string") {
        return `${errorMessage}: ${errorBody.detail}`;
      }

      if (errorBody?.detail !== undefined) {
        return `${errorMessage}: ${JSON.stringify(errorBody.detail)}`;
      }

      if (typeof errorBody?.message === "string" && errorBody.message.trim().length > 0) {
        return `${errorMessage}: ${errorBody.message}`;
      }

      return errorMessage;
    }

    const text = await response.text();
    if (text.trim().length > 0) {
      return `${errorMessage}: ${text}`;
    }

    return errorMessage;
  } catch {
    return errorMessage;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    token,
    organizationId,
    headers,
    body,
    jsonBody,
    responseType = "json",
    ...rest
  } = options;

  const resolvedToken = token ?? getStoredAccessToken();
  const resolvedTokenType = getStoredTokenType();
  const resolvedOrganizationId =
    organizationId ?? getStoredOrganizationId() ?? DEFAULT_ORGANIZATION_ID;

  const normalizedHeaders = normalizeHeaders(headers);
  const resolvedBody = resolveRequestBody({ body, jsonBody });

  const shouldSetAcceptHeader = !normalizedHeaders.Accept;
  const shouldSetContentTypeHeader =
    resolvedBody.shouldSetJsonContentType &&
    !normalizedHeaders["Content-Type"] &&
    !normalizedHeaders["content-type"];

  const response = await fetch(buildApiUrl(path), {
    ...rest,
    body: resolvedBody.body,
    headers: {
      ...(shouldSetAcceptHeader ? { Accept: "application/json" } : {}),
      ...(shouldSetContentTypeHeader ? { "Content-Type": "application/json" } : {}),
      ...(resolvedToken ? { Authorization: `${resolvedTokenType} ${resolvedToken}` } : {}),
      ...(resolvedOrganizationId ? { "X-Organization-Id": resolvedOrganizationId } : {}),
      ...normalizedHeaders,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response));
  }

  return parseResponseBody<T>(response, responseType);
}

export const apiClient = {
  get: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "POST",
      ...(isFormData(body) ||
      typeof body === "string" ||
      isBlob(body) ||
      isArrayBuffer(body) ||
      body instanceof URLSearchParams
        ? { body: body as BodyInit }
        : body !== undefined
          ? { jsonBody: body }
          : {}),
    }),

  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      ...(isFormData(body) ||
      typeof body === "string" ||
      isBlob(body) ||
      isArrayBuffer(body) ||
      body instanceof URLSearchParams
        ? { body: body as BodyInit }
        : body !== undefined
          ? { jsonBody: body }
          : {}),
    }),

  put: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "PUT",
      ...(isFormData(body) ||
      typeof body === "string" ||
      isBlob(body) ||
      isArrayBuffer(body) ||
      body instanceof URLSearchParams
        ? { body: body as BodyInit }
        : body !== undefined
          ? { jsonBody: body }
          : {}),
    }),

  delete: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "DELETE" }),

  getBlob: (path: string, options: RequestOptions = {}) =>
    request<Blob>(path, { ...options, method: "GET", responseType: "blob" }),

  getText: (path: string, options: RequestOptions = {}) =>
    request<string>(path, { ...options, method: "GET", responseType: "text" }),

  raw: <T>(path: string, options: RequestOptions = {}) => request<T>(path, options),
};