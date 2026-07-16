/** Types aligned with docs/api-spec.md and docs/rbac.md */

export type Role = "student" | "mentor" | "admin";

export type SessionStatus =
  | "created"
  | "queued"
  | "pre_eval"
  | "validation_running"
  | "ethics_running"
  | "tipsc_running"
  | "waiting_for_founder"
  | "tipsc_reevaluation"
  | "tipsc_completed"
  | "tipsc_failed"
  | "dfv_waiting"
  | "dfv_running"
  | "dfv_completed"
  | "dfv_failed"
  | "discovery_waiting"
  | "discovery_running"
  | "discovery_failed"
  | "completed"
  | "failed"
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
  customer_segment: string;
  consequence: string;
  assumptions?: string[];
  proposed_solution: string;
  target_geography: string;
  industry_sector: string;
  team_id?: string | null;
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
  customer_segment?: string;
  consequence?: string;
  assumptions?: string[];
  proposed_solution?: string;
  target_geography?: string;
  industry_sector?: string;
  idea: string;
  status: SessionStatus;
  
  preeval?: Record<string, unknown> | null;
  validation?: Record<string, unknown> | null;
  regulatory?: Record<string, unknown> | null;
  ethics?: Record<string, unknown> | null;
  compliance_context?: string | null;

  tipsc: Record<string, unknown> | null;
  dfv: Record<string, unknown> | null;
  discovery: Record<string, unknown> | null;

  pending_question?: string | null;
  followup_turn?: number;
  followup_history?: Array<{ question: string; answer: string; turn: number; answered_at: string }>;

  created_at: string;
  updated_at: string;
};

export type MentorComment = {
  comment_id: string;
  mentor_name: string;
  comment: string;
  created_at: string;
};
