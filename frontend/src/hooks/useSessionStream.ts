import { useEffect, useRef } from "react";
import { API_BASE_URL } from "@/constants";
import { getAccessToken } from "@/services/apiClient";
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
    let abortController = new AbortController();

    const connectStream = async () => {
      try {
        const token = getAccessToken();
        const streamUrl = token
            ? `${API_BASE_URL}/sessions/${sessionId}/stream?token=${encodeURIComponent(token)}`
            : `${API_BASE_URL}/sessions/${sessionId}/stream`;

        const response = await fetch(streamUrl, {
          // Keep the header too for non-EventSource usage:
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: abortController.signal,
        });

        if (!response.body) return;

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (active) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          
          buffer = lines.pop() || ""; // keep the last incomplete chunk

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.substring(6)) as SessionDocument;
                onUpdateRef.current(data);
              } catch (err) {
                console.error("Failed to parse SSE data", err);
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === "AbortError") return;
        console.error("SSE connection error", err);
        // Basic reconnect logic
        if (active) {
          setTimeout(connectStream, 5000);
        }
      }
    };

    connectStream();

    return () => {
      active = false;
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
