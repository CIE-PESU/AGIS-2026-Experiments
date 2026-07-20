export type Role = "student" | "mentor" | "admin";

export type SessionStatus =
| "created"
| "queued"
| "pre_eval"
| "validation_running"
| "regulatory_running"
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

export interface PreEvaluationResult {
problem_statement: string;
customer_segment: string;
consequence: string;
assumptions: string[];
proposed_solution: string;
target_geography: string;
industry_sector: string;
}

export interface CheckedAssumption {
assumption: string;
verdict: "CONFIRMED" | "PARTIAL" | "REJECTED";
evidence: string;
}

export interface ValidationResult {
target_geography: string;
industry_sector: string;
checked_assumptions: CheckedAssumption[];
competitor_landscape: string;
market_notes: string;
validation_summary: "STRONG" | "MODERATE" | "WEAK";
}

export interface ApplicableRegulation {
name: string;
jurisdiction: string;
brief_requirement: string;
compliance_burden: "LOW" | "MEDIUM" | "HIGH";
}

export interface RegulatoryResult {
target_geography: string;
industry_sector: string;
applicable_regulations: ApplicableRegulation[];
regulatory_summary: string;
requires_specialist_review: boolean;
key_compliance_risks: string[];
}

export interface EthicsResult {
harm_vector: "GREEN" | "YELLOW" | "RED";
harm_reason: string;

legal_risk: "GREEN" | "YELLOW" | "RED";
legal_reason: string;

problem_solution_integrity: "GREEN" | "YELLOW" | "RED";
integrity_reason: string;

ethics_pass: boolean;
compliance_flag: boolean;

rejection_reason?: string | null;
}

export interface CriteriaState {
  T: "resolved" | "weak";
  I: "resolved" | "weak";
  P: "resolved" | "weak";
  S: "resolved" | "weak";
}

export interface TipsRagScores {
  T: "GREEN" | "YELLOW" | "RED";
  I: "GREEN" | "YELLOW" | "RED";
  P: "GREEN" | "YELLOW" | "RED";
  S: "GREEN" | "YELLOW" | "RED";

  T_reason: string;
  I_reason: string;
  P_reason: string;
  S_reason: string;
}

export interface RefinedIdea {
  customer_segment: string;
  qualified_problem: string;
  consequence: string;
  proposed_solution: string;
}

export interface TipsValidatedMetrics {
  timely_factor: string;
  importance_metric: string;
  profitability_pivot: string;
  solvability_constraint: string;
}

export interface TIPSCResult {
  refined_idea: RefinedIdea;

  solution_alignment: "GREEN" | "YELLOW" | "RED";

  tips_validated_metrics: TipsValidatedMetrics;

  tips_rag_scores: TipsRagScores;

  overall_readiness: "HIGH" | "MODERATE" | "LOW";

  ready_for_dfv: boolean;

  needs_followup: boolean;

  missing_criteria: ("T" | "I" | "P" | "S")[];

  criteria_state: CriteriaState;

  reasoning: string;

  compliance_flag: boolean;

  followups_asked: number;

  completed_at: string | null;
}

export interface DFVResult {
desirability: CriteriaState;
feasibility: CriteriaState;
viability: CriteriaState;
summary: string;
}

export interface DiscoveryResult {
findings: string[];
next_steps: string[];
}

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

preeval?: PreEvaluationResult | null;
validation?: ValidationResult | null;
regulatory?: RegulatoryResult | null;
ethics?: EthicsResult | null;
compliance_context?: string | null;

tipsc?: TIPSCResult | null;
dfv?: DFVResult | null;
discovery?: DiscoveryResult | null;

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