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

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
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

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!response.ok) {
    clearTokens();
    return false;
  }

  const body = (await response.json()) as ApiSuccess<{ access_token: string; refresh_token: string }>;
  setTokens(body.data.access_token, body.data.refresh_token);
  return true;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  idempotencyKey?: string;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, idempotencyKey } = options;

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
      body: body !== undefined ? JSON.stringify(body) : undefined
    });

  let response = await send();

  if (response.status === 401 && auth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) response = await send();
  }

  if (response.status === 204) return undefined as T;

  if (!response.ok) throw await parseError(response);

  const payload = (await response.json()) as ApiSuccess<T>;
  return payload.data;
}
