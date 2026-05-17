import { buildApiUrl } from "@/lib/config";
import { clearAuth, getAccessToken, getOrganizationId, getTokenType } from "@/lib/auth";

type RequestOptions = Omit<RequestInit, "body"> & {
  token?: string;
  dedupe?: boolean;
  retry?: boolean;
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

const inFlightGetRequests = new Map<string, Promise<unknown>>();
let activeApiRequests = 0;
const queuedApiRequests: Array<() => void> = [];

function isMobileSafariRuntime(): boolean {
  if (typeof navigator === "undefined") {
    return false;
  }
  const ua = navigator.userAgent;
  return /iP(ad|hone|od)/.test(ua) && /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
}

function maxConcurrentApiRequests(): number {
  return isMobileSafariRuntime() ? 2 : 4;
}

async function withApiRequestSlot<T>(runner: () => Promise<T>): Promise<T> {
  if (activeApiRequests >= maxConcurrentApiRequests()) {
    await new Promise<void>((resolve) => queuedApiRequests.push(resolve));
  }
  activeApiRequests += 1;
  try {
    return await runner();
  } finally {
    activeApiRequests = Math.max(0, activeApiRequests - 1);
    const next = queuedApiRequests.shift();
    if (next) {
      next();
    }
  }
}

function dedupeKey(path: string, options: RequestOptions): string {
  const method = (options.method ?? "GET").toUpperCase();
  return JSON.stringify({
    method,
    path,
    organizationId: options.organizationId ?? getOrganizationId() ?? null,
    authMode: options.authMode ?? "auto",
    responseType: options.responseType ?? "json",
  });
}

function shouldRetryRequest(error: unknown): boolean {
  if (error instanceof ApiClientError) {
    return [429, 502, 503, 504].includes(error.status);
  }
  return error instanceof TypeError;
}

function backoffDelayMs(attempt: number): number {
  const base = 250 * 2 ** Math.max(0, attempt - 1);
  return base + Math.floor(Math.random() * 100);
}

function delay(ms: number, signal?: AbortSignal | null): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = globalThis.setTimeout(resolve, ms);
    const onAbort = () => {
      globalThis.clearTimeout(timeout);
      reject(new DOMException("Request was canceled", "AbortError"));
    };
    if (signal) {
      if (signal.aborted) {
        onAbort();
        return;
      }
      signal.addEventListener("abort", onAbort, { once: true });
    }
  });
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

function logApiClientDiagnostic(message: string, details: Record<string, unknown>): void {
  if (typeof console === "undefined") {
    return;
  }

  console.warn(message, details);
}

async function performRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
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
    dedupe,
    retry,
    ...rest
  } = options;

  void dedupe;
  void retry;

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
  let didTimeout = false;
  const timeout = timeoutMs > 0
    ? globalThis.setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, timeoutMs)
    : null;
  const abortFromCaller = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      abortFromCaller();
    } else {
      signal.addEventListener("abort", abortFromCaller, { once: true });
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
      const durationMs = Date.now() - startedAt;
      const method = rest.method ?? "GET";
      logApiClientDiagnostic("API request aborted", {
        path,
        method,
        durationMs,
        timeoutMs,
        reason: didTimeout ? "client_timeout" : "caller_abort",
      });
      throw new ApiClientError(
        didTimeout
          ? `Request timed out after ${timeoutMs}ms (${method} ${path}). Please try again.`
          : `Request was canceled (${method} ${path}). Please try again.`,
        {
          status: didTimeout ? 504 : 499,
          code: didTimeout ? "client_timeout" : "client_aborted",
          details: { path, method, durationMs, timeoutMs },
        }
      );
    }
    throw caught;
  } finally {
    if (timeout !== null) {
      globalThis.clearTimeout(timeout);
    }
    if (signal) {
      signal.removeEventListener("abort", abortFromCaller);
    }
  }

  const durationMs = Date.now() - startedAt;
  if (durationMs >= 2_000) {
    logApiClientDiagnostic("Slow API request", { path, method: rest.method ?? "GET", durationMs, status: response.status });
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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const shouldDedupe = method === "GET" && options.dedupe !== false;
  const key = shouldDedupe ? dedupeKey(path, options) : null;
  if (key && inFlightGetRequests.has(key)) {
    return inFlightGetRequests.get(key) as Promise<T>;
  }

  const runner = async () => {
    const maxAttempts = options.retry === false ? 1 : method === "GET" ? 2 : 1;
    let attempt = 0;
    let lastError: unknown;
    while (attempt < maxAttempts) {
      attempt += 1;
      try {
        return await withApiRequestSlot(() => performRequest<T>(path, options));
      } catch (caught: unknown) {
        lastError = caught;
        if (attempt >= maxAttempts || !shouldRetryRequest(caught)) {
          throw caught;
        }
        await delay(backoffDelayMs(attempt), options.signal ?? null);
      }
    }
    throw lastError;
  };

  const promise = runner();
  if (key) {
    inFlightGetRequests.set(key, promise);
    promise.finally(() => inFlightGetRequests.delete(key));
  }
  return promise;
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
