import { useEffect, useState } from "react";
import { MessageSquare } from "lucide-react";
import { getSessionComments } from "@/services/authSessions";
import type { MentorComment } from "@/types/api";

export function MentorChat({ sessionId }: { sessionId: string | null }) {
  const [comments, setComments] = useState<MentorComment[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(sessionId));
  const [loadedSessionId, setLoadedSessionId] = useState<string | null>(null);

  useEffect(() => {
    setComments([]);
    setLoadedSessionId(sessionId);
    setError(null);
    setLoading(Boolean(sessionId));
    if (!sessionId) return;
    let active = true;
    getSessionComments(sessionId)
      .then((res) => {
        if (!Array.isArray(res)) throw new Error("Invalid comments response");
        if (active) setComments(res);
      })
      .catch(() => {
        if (active) setError("Mentor comments could not be loaded. Refresh to retry.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
        <MessageSquare className="mx-auto mb-2 h-8 w-8" />
        Start a session to view mentor comments.
      </div>
    );
  }

  if (loading || loadedSessionId !== sessionId) return <p role="status" className="p-4 text-sm text-muted-foreground">Loading mentor comments…</p>;
  if (error) return <p role="alert" className="rounded-lg border border-destructive/30 p-4 text-sm text-destructive">{error}</p>;

  if (comments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
        <MessageSquare className="mx-auto mb-2 h-8 w-8" />
        No mentor comments yet. Mentors can add comments on your session (read-only for students).
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {comments.map((message) => (
        <div key={message.comment_id} className="flex gap-3 rounded-lg bg-muted/60 p-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
            {message.mentor_name.charAt(0)}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">{message.mentor_name}</p>
              <p className="text-xs text-muted-foreground">{message.created_at}</p>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{message.comment}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
