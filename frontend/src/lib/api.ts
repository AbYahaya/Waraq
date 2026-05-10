/**
 * Typed fetch wrapper for the Waraq backend.
 *
 * The backend exposes auth-protected endpoints that expect
 * `Authorization: Bearer <token>`. The token lives in the auth Zustand
 * store; this module reads it lazily on each request to avoid stale
 * closures and so logout immediately stops sending the bearer.
 *
 * All non-2xx responses raise `ApiError` with the parsed `detail` from
 * the backend's ErrorResponse shape — TanStack Query catches it and the
 * UI surfaces it.
 */

import { useAuthStore } from "@/store/auth";

const API_PREFIX = "/api";

export const apiPath = (path: string): string =>
  path.startsWith("http") ? path : `${API_PREFIX}${path}`;

export class ApiError extends Error {
  status: number;
  detail: string;
  body: unknown;
  constructor(status: number, detail: string, body: unknown) {
    super(`HTTP ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

export type ApiInit = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown;
  headers?: Record<string, string>;
  /** When true (default), attaches the bearer token. Set false for /auth/login etc. */
  auth?: boolean;
};

async function request<T>(path: string, init: ApiInit = {}): Promise<T> {
  const { body, headers = {}, auth = true, ...rest } = init;

  const finalHeaders: Record<string, string> = { ...headers };
  let payload: BodyInit | undefined;

  if (body !== undefined) {
    if (body instanceof FormData) {
      payload = body;
    } else {
      payload = JSON.stringify(body);
      finalHeaders["Content-Type"] ??= "application/json";
    }
  }

  if (auth) {
    const token = useAuthStore.getState().token;
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(apiPath(path), { ...rest, body: payload, headers: finalHeaders });

  if (resp.status === 401 && auth) {
    // Server told us the token is gone or expired — drop it and let the
    // route guard redirect to /login on the next render tick.
    useAuthStore.getState().logout();
  }

  const contentType = resp.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const parsed = isJson ? await resp.json().catch(() => null) : await resp.text();

  if (!resp.ok) {
    const detail =
      isJson && parsed && typeof parsed === "object" && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : String(parsed ?? resp.statusText);
    throw new ApiError(resp.status, detail, parsed);
  }

  return parsed as T;
}

export const api = {
  get: <T>(path: string, init?: Omit<ApiInit, "body">) =>
    request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>(path, { ...init, method: "POST", body }),
  put: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>(path, { ...init, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>(path, { ...init, method: "PATCH", body }),
  delete: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>(path, { ...init, method: "DELETE", body }),
};
