/**
 * services/api.ts — Real API calls replacing the original mock implementations.
 *
 * Previously all functions here returned static mock data via wait().
 * They now call the real backend.
 *
 * NOTE: TIPSC scores and compliance data are NOT polled here — they are pushed
 * via the SSE stream (useSessionStream hook). TIPSCFlow.tsx should read from
 * AuthContext.results and AuthContext.serverStatus instead of calling these functions.
 *
 * The only function remaining here is submitFollowup (the actual POST endpoint).
 */

import { apiRequest } from "@/services/apiClient";
import { USE_MOCK_FLOWS } from "@/constants";

// ---------------------------------------------------------------------------
// Mock data (used only when USE_MOCK_FLOWS=true / backend unavailable)
// ---------------------------------------------------------------------------

import {
  mockComplianceResult,
  mockTIPSCInitial,
  mockTIPSCAfterRound1,
  mockTIPSCFinal,
} from "@/data/mockData";

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// Follow-up answer submission
// POST /sessions/user/{studentId}/followup
// ---------------------------------------------------------------------------

export async function submitFollowup(
  studentId: string,
  answer: string
): Promise<{ status: string; session_id: string }> {
  if (USE_MOCK_FLOWS) {
    await wait(1200);
    return { status: "accepted", session_id: "mock_session_id" };
  }
  return apiRequest<{ status: string; session_id: string }>(
    `/sessions/user/${studentId}/followup`,
    {
      method: "POST",
      body: JSON.stringify({ answer }),
    }
  );
}

// ---------------------------------------------------------------------------
// DEPRECATED — these are kept to avoid breaking imports but are no longer
// the correct way to get TIPSC data. Use AuthContext.results.tips instead.
// The SSE stream pushes TIPSC data when the backend completes evaluation.
// ---------------------------------------------------------------------------

/** @deprecated — use AuthContext.results.tips from the SSE stream */
export async function getInitialTIPSCScores(sessionId: string): Promise<typeof mockTIPSCInitial> {
  if (USE_MOCK_FLOWS) {
    await wait(2000);
    return mockTIPSCInitial;
  }
  // SSE-driven — this endpoint does not exist. Return from session GET instead.
  return apiRequest<typeof mockTIPSCInitial>(`/sessions/${sessionId}`).then(
    (session: any) => session?.tipsc ?? mockTIPSCInitial
  );
}

/** @deprecated — compliance data is in AuthContext.results.tips.compliance_flag */
export async function checkCompliance(sessionId: string): Promise<typeof mockComplianceResult> {
  if (USE_MOCK_FLOWS) {
    await wait(1500);
    return mockComplianceResult;
  }
  return apiRequest<typeof mockComplianceResult>(`/sessions/${sessionId}`).then(
    (session: any) => session?.tipsc?.compliance_flag ?? mockComplianceResult
  );
}

/** @deprecated — use submitFollowup(studentId, answer) instead */
export async function submitFollowUp(
  _sessionId: string,
  _answer: string
): Promise<(typeof mockTIPSCAfterRound1 | typeof mockTIPSCFinal)> {
  if (USE_MOCK_FLOWS) {
    await wait(1500);
    return mockTIPSCAfterRound1;
  }
  console.warn("submitFollowUp is deprecated. Use submitFollowup(studentId, answer) instead.");
  return mockTIPSCAfterRound1;
}

export { mockTIPSCAfterRound1, mockTIPSCFinal };

// ---------------------------------------------------------------------------
// Compatibility stubs — imported by DFVFlow/DiscoveryFlow but not called
// (those flows use triggerDfv / triggerDiscovery from authSessions instead)
// ---------------------------------------------------------------------------

import { mockDFVResult, mockJTBDResult } from "@/data/mockData";

/** @deprecated — DFVFlow uses triggerDfv() from authSessions, not this function */
export async function runDFVAnalysis(_sessionId: string): Promise<typeof mockDFVResult> {
  await wait(1500);
  return mockDFVResult;
}

/** @deprecated — DiscoveryFlow uses triggerDiscovery() from authSessions, not this function */
export async function generateJTBD(_sessionId: string): Promise<typeof mockJTBDResult> {
  await wait(1500);
  return mockJTBDResult;
}

