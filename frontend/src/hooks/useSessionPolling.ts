import { useEffect, useRef } from "react";
import { SESSION_POLL_INTERVAL_MS } from "@/constants";
import { getSession } from "@/services/authSessions";
import type { SessionDocument } from "@/types/api";
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
    let inFlight = false;

    const poll = async () => {
      if (!active || inFlight) return;
      inFlight = true;
      try {
        const session = await getSession(sessionId);

        if (active) {
          onUpdateRef.current(session);
        }
      } catch (err: any) {
        if (err?.status === 401) {
          active = false;
          return;
        }
        if (err?.status === 404) {
          console.warn("Session no longer exists.");

          if (active) {
            active = false;
            onNotFound();
          }

          return;
        }

        console.error("Polling failed:", err);
      } finally {
        inFlight = false;
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
