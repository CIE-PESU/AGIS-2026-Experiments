/** Types aligned with docs/api-spec.md and docs/rbac.md */

export type Role = "student" | "mentor" | "admin";

export type SessionStatus =
  | "created"
  | "queued"
  | "tipsc_running"
  | "tipsc_completed"
  | "tipsc_failed"
  | "waiting_for_founder"
  | "dfv_waiting"
  | "dfv_running"
  | "dfv_completed"
  | "dfv_failed"
  | "discovery_waiting"
  | "discovery_running"
  | "discovery_failed"
  | "completed"
  | "archived";

export type ApiMeta = {
  request_id: string;
  timestamp: string;
};

export type ApiError = {
  code: string;
  message: string;
  field?: string | null;
  request_id: string;
  timestamp: string;
};

export type ApiSuccess<T> = {
  data: T;
  meta?: ApiMeta;
};

export type PaginatedResponse<T> = ApiSuccess<T[]> & {
  pagination: {
    page: number;
    limit: number;
    total: number;
    has_next: boolean;
    has_prev: boolean;
  };
};

export type AuthUser = {
  user_id: string;
  name: string;
  srn: string;
  email?: string;
  role: Role;
  team_id?: string | null;
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  role: Role;
  user: AuthUser;
};

export type RefreshResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

export type CreateSessionRequest = {
  problem_statement: string;
  idea: string;
};

export type CreateSessionResponse = {
  session_id: string;
  status: SessionStatus;
  created_at: string;
};

export type TriggerDfvRequest = {
  desirability_context: string;
  feasibility_context: string;
  viability_context: string;
};

export type SessionDocument = {
  session_id: string;
  team_id: string;
  student_id: string;
  problem_statement: string;
  idea: string;
  status: SessionStatus;
  /** Flat TIPSCOutput object from backend — no .output wrapper */
  tipsc?: {
    tips_rag_scores?: {
      T?: string; I?: string; P?: string; S?: string;
      T_reason?: string; I_reason?: string; P_reason?: string; S_reason?: string;
    };
    ready_for_dfv?: boolean;
    needs_followup?: boolean;
    overall_readiness?: string;
    compliance_flag?: boolean;
    reasoning?: string;
    followups_asked?: number;
    completed_at?: string;
  } | null;
  /** DFV output — .output may or may not be nested */
  dfv?: {
    status?: string;
    output?: Record<string, any>;
    error?: string;
    completed_at?: string;
  } | null;
  /** Discovery output — same shape as DFV */
  discovery?: {
    status?: string;
    output?: Record<string, any>;
    error?: string;
    completed_at?: string;
  } | null;
  created_at: string;
  updated_at: string;
};

export type MentorComment = {
  comment_id: string;
  mentor_name: string;
  comment: string;
  created_at: string;
};
