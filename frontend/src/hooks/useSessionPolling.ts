import { useEffect, useRef } from "react";
import { SESSION_POLL_INTERVAL_MS } from "@/constants";
import { getSession } from "@/services/authSessions";
import type { SessionDocument } from "@/types/api";

export function useSessionPolling(
  sessionId: string | null,
  onUpdate: (session: SessionDocument) => void,
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
        if (active) onUpdateRef.current(session);
      } catch {
        // Polling errors are handled by the caller / auth layer
      }
    };

    poll();
    const timer = window.setInterval(poll, SESSION_POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [sessionId, enabled]);
}

/** Map backend session status to UI stage unlock state */
export function deriveStageAccess(status: SessionDocument["status"]) {
  const tipscDone = ["tipsc_completed", "dfv_waiting", "dfv_running", "dfv_completed", "dfv_failed", "discovery_waiting", "discovery_running", "discovery_failed", "completed"].includes(status);
  const dfvDone = ["dfv_completed", "discovery_waiting", "discovery_running", "discovery_failed", "completed"].includes(status);
  const discoveryDone = status === "completed";

  return {
    tipsc: tipscDone ? "completed" as const : status.includes("tipsc") || status === "queued" || status === "created" ? "in_progress" as const : "available" as const,
    dfv: !tipscDone ? "locked" as const : dfvDone ? "completed" as const : status.includes("dfv") ? "in_progress" as const : "available" as const,
    discovery: !dfvDone ? "locked" as const : discoveryDone ? "completed" as const : status.includes("discovery") ? "in_progress" as const : "available" as const
  };
}

export function isFlowRunning(status: SessionDocument["status"]) {
  return status.endsWith("_running") || status === "queued";
}
