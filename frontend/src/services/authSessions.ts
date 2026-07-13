import { apiRequest, clearTokens, setTokens } from "@/services/apiClient";
import type {
  AuthUser,
  CreateSessionRequest,
  CreateSessionResponse,
  LoginResponse,
  MentorComment,
  RefreshResponse,
  SessionDocument,
  TriggerDfvRequest
} from "@/types/api";

export async function login(srn: string, password: string): Promise<LoginResponse> {
  const data = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: { srn, password },
    auth: false
  });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  try {
    await apiRequest<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
      auth: true
    });
  } finally {
    clearTokens();
  }
}

export async function getCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me");
}

export async function createSession(
  payload: CreateSessionRequest,
  idempotencyKey?: string
): Promise<CreateSessionResponse> {
  return apiRequest<CreateSessionResponse>("/sessions", {
    method: "POST",
    body: payload,
    idempotencyKey
  });
}

export async function getSession(sessionId: string): Promise<SessionDocument> {
  return apiRequest<SessionDocument>(`/sessions/${sessionId}`);
}

export async function archiveSession(sessionId: string): Promise<{ session_id: string; status: string; archived_at: string }> {
  return apiRequest(`/sessions/${sessionId}`, { method: "DELETE" });
}

export async function triggerTipsc(sessionId: string) {
  return apiRequest(`/sessions/${sessionId}/trigger/tipsc`, { method: "POST" });
}

export async function triggerDfv(sessionId: string, payload: TriggerDfvRequest) {
  return apiRequest(`/sessions/${sessionId}/trigger/dfv`, { method: "POST", body: payload });
}

export async function triggerDiscovery(sessionId: string) {
  return apiRequest(`/sessions/${sessionId}/trigger/discovery`, { method: "POST" });
}

export async function getSessionComments(sessionId: string): Promise<MentorComment[]> {
  return apiRequest<MentorComment[]>(`/sessions/${sessionId}/comments`);
}

export async function getMentorSessions(params?: { team_id?: string; status?: string; page?: number; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.team_id) query.set("team_id", params.team_id);
  if (params?.status) query.set("status", params.status);
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest(`/mentor/sessions${suffix}`);
}

export type { RefreshResponse };
