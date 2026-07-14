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
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/stream`, {
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

/** Map backend session status to UI stage unlock state */
export function deriveStageAccess(status: SessionDocument["status"]) {
  const tipscDone = ["tipsc_completed", "dfv_waiting", "dfv_running", "dfv_completed", "dfv_failed", "discovery_waiting", "discovery_running", "discovery_failed", "completed"].includes(status);
  const dfvDone = ["dfv_completed", "discovery_waiting", "discovery_running", "discovery_failed", "completed"].includes(status);
  const discoveryDone = status === "completed";

  return {
    tipsc: tipscDone ? "completed" as const : status.includes("tipsc") || status === "queued" || status === "created" || status === "waiting_for_founder" ? "in_progress" as const : "available" as const,
    dfv: !tipscDone ? "locked" as const : dfvDone ? "completed" as const : status.includes("dfv") ? "in_progress" as const : "available" as const,
    discovery: !dfvDone ? "locked" as const : discoveryDone ? "completed" as const : status.includes("discovery") ? "in_progress" as const : "available" as const
  };
}

export function isFlowRunning(status: SessionDocument["status"]) {
  return status.endsWith("_running") || status === "queued";
}
