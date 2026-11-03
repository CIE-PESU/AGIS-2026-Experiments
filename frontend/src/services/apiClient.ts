import { API_BASE_URL } from "@/constants";
import type { ApiError, ApiSuccess } from "@/types/api";

const ACCESS_TOKEN_KEY = "agis_access_token";
const REFRESH_TOKEN_KEY = "agis_refresh_token";

export class ApiRequestError extends Error {
  status: number;
  code: string;
  requestId?: string;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.status = status;
    this.code = error.code;
    this.requestId = error.request_id;
  }
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function setAccessTokenOnly(accessToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event("agis:auth-cleared"));
}

async function parseError(response: Response): Promise<ApiRequestError> {
  try {
    const body = (await response.json()) as { error: ApiError };
    return new ApiRequestError(response.status, body.error);
  } catch {
    return new ApiRequestError(response.status, {
      code: "INTERNAL_ERROR",
      message: response.statusText || "Request failed",
      request_id: "",
      timestamp: new Date().toISOString()
    });
  }
}

let refreshInFlight: { token: string; promise: Promise<boolean> } | null = null;

export function refreshAccessToken(): Promise<boolean> {
  const token = getRefreshToken();
  if (!token) return Promise.resolve(false);
  if (!refreshInFlight || refreshInFlight.token !== token) {
    const promise = performRefresh(token).finally(() => {
      if (refreshInFlight?.promise === promise) refreshInFlight = null;
    });
    refreshInFlight = { token, promise };
  }
  return refreshInFlight.promise;
}

async function performRefresh(refreshToken: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  // A logout or a different login can finish while this request is in flight.
  if (getRefreshToken() !== refreshToken) return false;

  if (!response.ok) {
    if (response.status !== 401 && response.status !== 403) throw await parseError(response);
    clearTokens();
    return false;
  }

  const body = (await response.json()) as ApiSuccess<{ access_token: string; refresh_token: string }>;
  if (getRefreshToken() !== refreshToken) return false;
  setTokens(body.data.access_token, body.data.refresh_token);
  return true;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  idempotencyKey?: string;
  signal?: AbortSignal;
  raw?: boolean;
};

export async function apiFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = "GET", body, auth = true, idempotencyKey } = options;

  if (auth && !getAccessToken()) {
    if (!await refreshAccessToken()) {
      if (!getAccessToken()) clearTokens();
      throw new ApiRequestError(401, {
        code: "TOKEN_INVALID",
        message: "Your session has ended. Please log in again.",
        request_id: "",
        timestamp: new Date().toISOString()
      });
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };

  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const send = () =>
    fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      signal: options.signal,
      body: body !== undefined ? JSON.stringify(body) : undefined
    });

  let response = await send();

  if (response.status === 401 && auth) {
    // A request from an older login must not refresh or clear the new login.
    if (headers.Authorization !== `Bearer ${getAccessToken()}`) {
      throw await parseError(response);
    }
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers.Authorization = `Bearer ${getAccessToken()}`;
      response = await send();
    }
    if (response.status === 401 && headers.Authorization === `Bearer ${getAccessToken()}`) clearTokens();
  }

  if (!response.ok) throw await parseError(response);
  return response;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await apiFetch(path, options);
  if (response.status === 204) return undefined as T;
  const payload = await response.json();
  return options.raw ? payload as T : payload.data as T;
}
