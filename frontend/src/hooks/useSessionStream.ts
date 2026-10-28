import { useEffect, useRef } from "react";
import { apiFetch } from "@/services/apiClient";
import type { SessionDocument } from "@/types/api";

export function useSessionStream(
  sessionId: string | null,
  onUpdate: (session: SessionDocument) => void,
  enabled = true
) {
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  useEffect(() => {
    if (!sessionId || !enabled) return;

    let active = true;
    const abortController = new AbortController();
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let delay = 1000;
    const connectStream = async () => {
      try {
        const response = await apiFetch(`/sessions/${sessionId}/stream`, { signal: abortController.signal });
        if (!response.body) throw new Error("Stream body missing");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        try {
          while (active) {
            const { value, done } = await reader.read();
            if (done) break;
            delay = 1000;
            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop() || "";
            for (const event of events) {
              const data = event.split(/\r?\n/).filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
              if (data) onUpdateRef.current(JSON.parse(data) as SessionDocument);
            }
          }
        } finally {
          await reader.cancel();
          reader.releaseLock();
        }
      } catch (error: unknown) {
        if (abortController.signal.aborted) return;
        if (error && typeof error === "object" && "status" in error && (error.status === 401 || error.status === 403 || error.status === 404)) return;
      }
      if (active) {
        reconnectTimer = setTimeout(connectStream, delay);
        delay = Math.min(delay * 2, 30000);
      }
    };
    void connectStream();
    return () => {
      active = false;
      clearTimeout(reconnectTimer);
      abortController.abort();
    };
  }, [sessionId, enabled]);
}

import { deriveCanonicalStageAccess } from "@/utils/sessionStatus";
import type { StageStatus } from "@/data/mockData";

/** Map backend session status to UI stage unlock state */
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
    discovery: toStageStatus(access.discovery)
  };
}

export function isFlowRunning(status: SessionDocument["status"]) {
  return (
    status.endsWith("_running") ||
    status === "queued" ||
    status === "pre_eval" ||
    status === "tipsc_reevaluation" ||
    status === "dfv_waiting" ||
    status === "discovery_waiting"
  );
}
