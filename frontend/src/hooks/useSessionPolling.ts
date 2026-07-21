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

/** Map backend session status to UI stage unlock state */
export function deriveStageAccess(doc: SessionDocument | null) {
  if (!doc || !doc.status) {
    return { tipsc: "available" as const, dfv: "locked" as const, discovery: "locked" as const };
  }

  const status = doc.status;

  const tipscDone = [
    "tipsc_completed",
    "dfv_waiting",
    "dfv_running",
    "dfv_completed",
    "dfv_failed",
    "discovery_waiting",
    "discovery_running",
    "discovery_failed",
    "completed",
    "failed"
  ].includes(status);

  const dfvDone = [
    "dfv_completed",
    "discovery_waiting",
    "discovery_running",
    "discovery_failed",
    "completed"
  ].includes(status);

  const discoveryDone = status === "completed";

  const tipscInProgress = [
    "created",
    "queued",
    "pre_eval",
    "validation_running",
    "ethics_running",
    "tipsc_running",
    "waiting_for_founder",
    "tipsc_reevaluation"
  ].includes(status);

  let dfvPassed = false;
  if (dfvDone && doc.dfv) {
    const dfvResult = (doc.dfv as any).output || doc.dfv;
    const decision = dfvResult?.decision ?? dfvResult?.final_decision?.status ?? "NO-GO";
    dfvPassed = decision === "GO";
  }

  return {
    tipsc: tipscDone ? ("completed" as const) : tipscInProgress ? ("in_progress" as const) : ("available" as const),
    dfv: !tipscDone ? ("locked" as const) : dfvDone ? ("completed" as const) : status.includes("dfv") || status === "dfv_waiting" ? ("in_progress" as const) : ("available" as const),
    discovery: (!dfvDone || (dfvDone && !dfvPassed)) ? ("locked" as const) : discoveryDone ? ("completed" as const) : status.includes("discovery") || status === "discovery_waiting" ? ("in_progress" as const) : ("available" as const)
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
    status === "discovery_waiting"
  );
}
