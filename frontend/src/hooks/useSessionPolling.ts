import { useEffect, useRef } from "react";
import { SESSION_POLL_INTERVAL_MS } from "@/constants";
import { getSession } from "@/services/authSessions";
import type { SessionDocument } from "@/types/api";
console.count("Session polling effect");
export function useSessionPolling(
  sessionId: string | null,
  onUpdate: (session: SessionDocument) => void,
  onNotFound: () => void,
  enabled = true
) {
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  useEffect(() => {
    if (!sessionId || !enabled) return;

    let active = true;

    const poll = async () => {
      try {
        const session = await getSession(sessionId);

        if (active) {
          onUpdateRef.current(session);
        }
      } catch (err: any) {
        if (err?.response?.status === 404) {
          console.warn("Session no longer exists.");

          if (active) {
            onNotFound();
          }

          return;
        }

        console.error("Polling failed:", err);
      }
    };

    poll();
    const timer = window.setInterval(poll, SESSION_POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [sessionId, enabled, onNotFound]);
}

import { deriveCanonicalStageAccess } from "@/utils/sessionStatus";
import type { StageStatus } from "@/data/mockData";

/** Map backend session status to UI stage unlock state — single canonical source of truth */
export function deriveStageAccess(doc: any | null) {
  const access = deriveCanonicalStageAccess(doc);
  const toStageStatus = (s: string): StageStatus => {
    if (s === "failed") return "failed";
    if (s === "GO" || s === "NO-GO") return "completed";
    return s as StageStatus;
  };
  return {
    tipsc: toStageStatus(access.tipsc),
    dfv: toStageStatus(access.dfv),
    discovery: toStageStatus(access.discovery),
    pmf: toStageStatus(access.pmf)
  };
}

export function isFlowRunning(status: SessionDocument["status"]) {
  if (!status) return false;
  return (
    status.endsWith("_running") ||
    status === "queued" ||
    status === "pre_eval" ||
    status === "tipsc_reevaluation" ||
    status === "dfv_waiting" ||
    status === "discovery_waiting" ||
    status === "pmf_waiting"
  );
}
