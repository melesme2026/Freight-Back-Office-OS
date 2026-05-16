import { buildApiUrl } from "@/lib/config";
import { clearAuth, getAccessToken, getOrganizationId, getTokenType } from "@/lib/auth";

type RequestOptions = Omit<RequestInit, "body"> & {
  token?: string;
  organizationId?: string;
  authMode?: "auto" | "none";
  onUnauthorized?: "redirect" | "throw";
  body?: BodyInit | null;
  jsonBody?: unknown;
  responseType?: "json" | "text" | "blob" | "response";
  timeoutMs?: number;
};

export class ApiClientError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string;
      details?: Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status;
    this.code = options.code;
    this.details = options.details;
  }
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

function isUrlSearchParams(value: unknown): value is URLSearchParams {
  return typeof URLSearchParams !== "undefined" && value instanceof URLSearchParams;
}

function isHtmlErrorText(value: string): boolean {
  return /<!doctype html|<html[\s>]/i.test(value.trim());
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

async function parseJsonSafely<T>(response: Response): Promise<T> {
  const text = await response.text();

  if (!text.trim()) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
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
    return parseJsonSafely<T>(response);
  }

  const text = await response.text();
  return text as T;
}

async function buildError(response: Response): Promise<ApiClientError> {
  const fallbackMessage = response.status === 403 ? "You do not have permission to access this page or resource." : "Something went wrong. Please try again.";

  try {
    const contentType = response.headers.get("content-type") ?? "";

    if (contentType.toLowerCase().includes("application/json")) {
      const errorBody = (await parseJsonSafely<{
        error?: { code?: string; message?: string; details?: Record<string, unknown> };
        organizations?: Array<Record<string, unknown>>;
        detail?: string | Array<unknown> | Record<string, unknown>;
        message?: string;
      }>(response)) as {
        error?: { code?: string; message?: string; details?: Record<string, unknown> };
        organizations?: Array<Record<string, unknown>>;
        detail?: string | Array<unknown> | Record<string, unknown>;
        message?: string;
      };

      if (typeof errorBody?.error === "string" && typeof errorBody?.message === "string") {
        return new ApiClientError(errorBody.message, {
          status: response.status,
          code: errorBody.error,
          details: Array.isArray(errorBody.organizations)
            ? { organizations: errorBody.organizations }
            : undefined,
        });
      }

      if (errorBody?.error?.message) {
        return new ApiClientError(errorBody.error.message, {
          status: response.status,
          code: errorBody.error.code,
          details: errorBody.error.details,
        });
      }

      if (typeof errorBody?.detail === "string") {
        return new ApiClientError(errorBody.detail, { status: response.status });
      }

      if (errorBody?.detail !== undefined) {
        if (typeof errorBody.detail === "object" && !Array.isArray(errorBody.detail)) {
          const detail = errorBody.detail as Record<string, unknown>;
          const message = typeof detail.message === "string" ? detail.message : fallbackMessage;
          const code = typeof detail.code === "string" ? detail.code : undefined;
          return new ApiClientError(message, {
            status: response.status,
            code,
            details: detail,
          });
        }

        return new ApiClientError(fallbackMessage, { status: response.status });
      }

      if (typeof errorBody?.message === "string" && errorBody.message.trim().length > 0) {
        return new ApiClientError(errorBody.message, { status: response.status });
      }
      return new ApiClientError(fallbackMessage, { status: response.status });
    }

    const text = await response.text();
    if (text.trim().length > 0 && !isHtmlErrorText(text)) {
      return new ApiClientError(text, { status: response.status });
    }
    return new ApiClientError(fallbackMessage, { status: response.status });
  } catch {
    return new ApiClientError(fallbackMessage, { status: response.status });
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    token,
    organizationId,
    authMode = "auto",
    onUnauthorized = "redirect",
    headers,
    body,
    jsonBody,
    responseType = "json",
    timeoutMs = 15_000,
    signal,
    ...rest
  } = options;

  const resolvedToken =
    authMode === "none" ? undefined : token ?? getAccessToken() ?? undefined;
  const resolvedTokenType = getTokenType();
  const resolvedOrganizationId =
    authMode === "none" ? undefined : organizationId ?? getOrganizationId() ?? undefined;

  const normalizedHeaders = normalizeHeaders(headers);
  const resolvedBody = resolveRequestBody({ body, jsonBody });

  const shouldSetAcceptHeader = !normalizedHeaders.Accept && !normalizedHeaders.accept;
  const shouldSetContentTypeHeader =
    resolvedBody.shouldSetJsonContentType &&
    !normalizedHeaders["Content-Type"] &&
    !normalizedHeaders["content-type"];

  const controller = new AbortController();
  const timeout = timeoutMs > 0
    ? globalThis.setTimeout(() => controller.abort(), timeoutMs)
    : null;
  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }

  const startedAt = Date.now();
  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), {
      ...rest,
      body: resolvedBody.body,
      signal: controller.signal,
      headers: {
        ...(shouldSetAcceptHeader ? { Accept: "application/json" } : {}),
        ...(shouldSetContentTypeHeader ? { "Content-Type": "application/json" } : {}),
        ...(resolvedToken ? { Authorization: `${resolvedTokenType} ${resolvedToken}` } : {}),
        ...(resolvedOrganizationId ? { "X-Organization-Id": resolvedOrganizationId } : {}),
        ...normalizedHeaders,
      },
      cache: "no-store",
    });
  } catch (caught: unknown) {
    if (isAbortError(caught)) {
      throw new ApiClientError("Request timed out. Please try again.", {
        status: 504,
        code: "client_timeout",
      });
    }
    throw caught;
  } finally {
    if (timeout !== null) {
      globalThis.clearTimeout(timeout);
    }
  }

  const durationMs = Date.now() - startedAt;
  if (durationMs >= 2_000 && typeof console !== "undefined") {
    console.warn("Slow API request", { path, method: rest.method ?? "GET", durationMs, status: response.status });
  }

  if (!response.ok) {
    if (
      response.status === 401 &&
      onUnauthorized === "redirect" &&
      typeof window !== "undefined"
    ) {
      const isDriverPortalRequest = window.location.pathname.startsWith("/driver-portal");
      clearAuth();
      const loginPath = isDriverPortalRequest ? "/driver-login" : "/login";
      window.location.replace(`${loginPath}?session=expired`);
    }

    throw await buildError(response);
  }

  return parseResponseBody<T>(response, responseType);
}

type MutationRequestBody = {
  body?: BodyInit;
  jsonBody?: unknown;
};

function resolveMutationBody(body?: unknown): MutationRequestBody {
  if (
    isFormData(body) ||
    typeof body === "string" ||
    isBlob(body) ||
    isArrayBuffer(body) ||
    isUrlSearchParams(body)
  ) {
    return { body: body as BodyInit };
  }

  if (body !== undefined) {
    return { jsonBody: body };
  }

  return {};
}

export const apiClient = {
  get: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "POST",
      ...resolveMutationBody(body),
    }),

  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      ...resolveMutationBody(body),
    }),

  put: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    request<T>(path, {
      ...options,
      method: "PUT",
      ...resolveMutationBody(body),
    }),

  delete: <T>(path: string, options: RequestOptions = {}) =>
    request<T>(path, { ...options, method: "DELETE" }),

  getBlob: (path: string, options: RequestOptions = {}) =>
    request<Blob>(path, { ...options, method: "GET", responseType: "blob" }),

  getText: (path: string, options: RequestOptions = {}) =>
    request<string>(path, { ...options, method: "GET", responseType: "text" }),

  raw: <T>(path: string, options: RequestOptions = {}) => request<T>(path, options),
};
