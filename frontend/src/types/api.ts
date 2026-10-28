export type Role = "student" | "mentor" | "mentor_workspace" | "admin";

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
| "pmf_waiting"
| "pmf_running"
| "pmf_completed"
| "pmf_failed"
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

export interface SeanEllisTest {
  very_disappointed_percentage: number;
  meets_target: boolean;
  analysis: string;
}

export interface NetPromoterScore {
  nps_score: number;
  meets_target: boolean;
  promoters_ratio: string;
}

export interface RetentionAnalysis {
  curve_trajectory: "Flattening" | "Smile Curve" | "Decaying" | string;
  value_creation_signal: "STRONG" | "MODERATE" | "WEAK" | string;
  summary: string;
}

export interface PMFMetrics {
  pmf_score: number;
  product_market_alignment: string;
  target_market_demand: string;
  value_proposition_strength: string;
  defensibility: string;
  sean_ellis_test?: SeanEllisTest;
  net_promoter_score?: NetPromoterScore;
  retention_analysis?: RetentionAnalysis;
}

export interface RiskAssessment {
  risk_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  key_risks: string[];
}

export interface PMFResult {
  correlation_id?: string;
  status?: string;
  output?: {
    pmf_metrics?: PMFMetrics;
    sean_ellis_test?: SeanEllisTest;
    net_promoter_score?: NetPromoterScore;
    retention_analysis?: RetentionAnalysis;
    executive_summary?: string;
    risk_assessment?: RiskAssessment;
    recommendations?: string[];
    raw?: string;
  };
  pmf_metrics?: PMFMetrics;
  sean_ellis_test?: SeanEllisTest;
  net_promoter_score?: NetPromoterScore;
  retention_analysis?: RetentionAnalysis;
  executive_summary?: string;
  risk_assessment?: RiskAssessment;
  recommendations?: string[];
  raw?: string;
  error?: string | null;
  started_at?: string;
  completed_at?: string;
}

export type SessionDocument = {
session_id: string;
team_id?: string | null;
student_id?: string | null;
workspace_id?: string | null;
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
pmf?: PMFResult | null;

pending_question?: string | null;
followup_turn?: number;
followup_history?: Array<{ question: string; answer: string; turn: number; answered_at: string }>;
error?: string | null;
rejection_reason?: string | null;

created_at: string;
updated_at: string;
};

export type MentorComment = {
comment_id: string;
mentor_name: string;
comment: string;
created_at: string;
};