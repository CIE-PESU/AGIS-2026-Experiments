export type Traffic = "green" | "yellow" | "red";
export type StageStatus = "locked" | "available" | "in_progress" | "completed" | "failed";

export type TIPSCScore = {
  status: Traffic;
  explanation: string;
};

export type TIPSCResult = {
  scores: Record<"timely" | "importance" | "profitable" | "solvable", TIPSCScore>;
  readyForDFV: boolean;
  explanation: string;
  followUps?: { question: string; answer: string }[];
};

export type DFVResult = {
  decision: "GO" | "NO-GO";
  executiveSummary: string;
  dimensions: Record<"desirability" | "feasibility" | "viability", { status: Traffic; summary: string; details: string[] }>;
  recommendations: string[];
};

export type JTBDResult = {
  title: string;
  objectives: {
    id: number;
    objective: string;
    whyItMatters: string;
    assumptionsValidated: string[];
    evidenceRequired: string[];
  }[];
  assumptions: {
    risk: "High Risk" | "Medium Risk" | "Low Risk";
    assumption: string;
    whyItMatters: string;
    evidenceRequired: string[];
    signals: { type: "validation" | "invalidation"; text: string }[];
  }[];
  interviewGuide: {
    section: string;
    subtitle: string;
    questions: string[];
  }[];
  executionGuide: {
    before: { title: string; items: string[] }[];
    during: { title: string; items: string[] }[];
    after: { title: string; items: string[] }[];
  };
  recordingTemplate: {
    profileFields: string[];
    contextFields: string[];
    problemEvidenceFields: { label: string; value?: string }[];
    behaviorFields: string[];
    frustrationFields: string[];
    motivationFields: string[];
    memorableQuotes: string[];
    unexpectedInsights: string;
  };
  evidenceChecklist: string[];
  finalSummary: {
    criticalAssumptions: string[];
    biggestRisks: string[];
    successfulInterviews: string[];
  };
};

export const preEvaluationQuestions = [
  { key: "problem", label: "Problem Statement", type: "textarea", prompt: "What problem are you solving?" },
  { key: "customer", label: "Customer Segment", type: "textarea", prompt: "Who experiences this problem most acutely?" },
  { key: "consequence", label: "Consequence", type: "textarea", prompt: "What happens if the problem remains unsolved?" },
  { key: "assumptions", label: "Assumptions", type: "textarea", prompt: "What assumptions are behind your idea?" },
  { key: "solution", label: "Proposed Solution", type: "textarea", prompt: "Describe your proposed solution." },
  { key: "geography", label: "Geography", type: "input", prompt: "Where will you begin?" },
  { key: "sector", label: "Industry Sector/Domain of Problem Statement", type: "input", prompt: "Which industry sector or domain does the problem statement belong to?" }
] as const;

