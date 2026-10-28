import type { SessionStatus } from "@/types/api";
import type { StageStatus } from "@/data/mockData";

export type SessionStageState = StageStatus | "failed" | "GO" | "NO-GO";

export interface SessionStageAccess {
  tipsc: SessionStageState;
  dfv: SessionStageState;
  discovery: SessionStageState;
  quickstart: SessionStageState;
  dfvDecision?: "GO" | "NO-GO" | string | null;
}

/**
 * Deterministic mapping table for all backend SessionStatus states.
 * Ensures 100% type-safe coverage — compiler error if any status is missing.
 */
const CANONICAL_STAGE_MAP: Record<
  SessionStatus,
  { tipsc: SessionStageState; dfv: SessionStageState; discovery: SessionStageState; quickstart: SessionStageState }
> = {
  // Session creation & TIPSC Pipeline
  created: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  queued: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  pre_eval: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  validation_running: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  regulatory_running: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  ethics_running: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  tipsc_running: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  waiting_for_founder: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  tipsc_reevaluation: { tipsc: "in_progress", dfv: "locked", discovery: "locked", quickstart: "available" },
  tipsc_failed: { tipsc: "failed", dfv: "locked", discovery: "locked", quickstart: "available" },

  // TIPSC Complete & DFV Pipeline
  tipsc_completed: { tipsc: "completed", dfv: "available", discovery: "locked", quickstart: "completed" },
  dfv_waiting: { tipsc: "completed", dfv: "in_progress", discovery: "locked", quickstart: "completed" },
  dfv_running: { tipsc: "completed", dfv: "in_progress", discovery: "locked", quickstart: "completed" },
  dfv_failed: { tipsc: "completed", dfv: "failed", discovery: "locked", quickstart: "completed" },

  // DFV Complete & Discovery Pipeline
  dfv_completed: { tipsc: "completed", dfv: "completed", discovery: "available", quickstart: "completed" },
  discovery_waiting: { tipsc: "completed", dfv: "completed", discovery: "in_progress", quickstart: "completed" },
  discovery_running: { tipsc: "completed", dfv: "completed", discovery: "in_progress", quickstart: "completed" },
  discovery_failed: { tipsc: "completed", dfv: "completed", discovery: "failed", quickstart: "completed" },

  // Terminal & Global states
  completed: { tipsc: "completed", dfv: "completed", discovery: "completed", quickstart: "completed" },
  failed: { tipsc: "failed", dfv: "locked", discovery: "locked", quickstart: "available" },
  archived: { tipsc: "available", dfv: "locked", discovery: "locked", quickstart: "available" }
};

/**
 * Single canonical stage status helper used across:
 * 1. Student Dashboard (cards)
 * 2. Mentor Dashboard (table)
 * 3. Team Progress Monitor (table)
 * 4. Detailed Progress View (modal)
 */
export function deriveCanonicalStageAccess(doc: any | null): SessionStageAccess {
  if (!doc || (!doc.status && !doc.sessionId)) {
    return {
      tipsc: "available",
      dfv: "locked",
      discovery: "locked",
      quickstart: "available",
      dfvDecision: null
    };
  }

  const status: string = typeof doc.status === "string" ? doc.status : doc.status?.value || "";

  // Single source of truth for DFV unlock gate: backend's ready_for_dfv boolean
  const readyForDFV = Boolean(doc?.tipsc?.ready_for_dfv);

  const mapped = CANONICAL_STAGE_MAP[status as SessionStatus] || {
    tipsc: "available",
    dfv: "locked",
    discovery: "locked",
    quickstart: "available"
  };

  let dfvStageState = mapped.dfv;
  // If TIPSC evaluation is complete, DFV is ONLY available if backend ready_for_dfv is true!
  if (status === "tipsc_completed") {
    dfvStageState = readyForDFV ? "available" : "locked";
  }

  let dfvDecision: string | null = null;
  const dfvRaw = doc.dfv_raw || doc.dfv || doc.dfv_status;
  if (typeof dfvRaw === "string" && (dfvRaw === "GO" || dfvRaw === "NO-GO")) {
    dfvDecision = dfvRaw;
  } else if (dfvRaw && typeof dfvRaw === "object") {
    const out = dfvRaw.output || dfvRaw;
    dfvDecision = out?.decision ?? out?.final_decision?.status ?? out?.overall_recommendation ?? null;
  }

  let dfvState = dfvStageState;
  if ((status === "dfv_completed" || status === "discovery_waiting" || status === "discovery_running" || status === "completed") && dfvDecision) {
    dfvState = dfvDecision as SessionStageState;
  }

  let discoveryState = mapped.discovery;
  if (mapped.dfv === "completed" && dfvDecision === "NO-GO" && status !== "completed") {
    discoveryState = "locked";
  }

  return {
    tipsc: mapped.tipsc,
    dfv: dfvState,
    discovery: discoveryState,
    quickstart: mapped.quickstart,
    dfvDecision
  };
}
