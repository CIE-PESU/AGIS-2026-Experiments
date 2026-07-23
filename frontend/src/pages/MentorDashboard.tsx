import { useEffect, useState, useCallback } from "react";
import { Navigate } from "react-router-dom";
import { Clock, Eye, LogOut, MessageSquare, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { SegmentedTabs } from "@/components/ui/tabs";
import { DetailedProgressView } from "@/components/shared/DetailedProgressView";
import { Logos } from "@/components/shared/Logos";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { getMentorSessions, getSessionComments, addComment as apiAddComment } from "@/services/authSessions";
import type { MentorComment } from "@/types/api";

// Shape returned by GET /mentor/sessions
interface MentorSession {
  session_id: string;
  team_id: string;
  team_name: string | null;
  student_name: string | null;
  status: string;
  tipsc_score: number | null;
  ready_for_dfv: boolean | null;
  created_at: string;
  updated_at: string;
}

export function MentorDashboard() {
  const { user, logout } = useAuth();

  const [sessions, setSessions] = useState<MentorSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [teamFilter, setTeamFilter] = useState<string>("");

  // comments keyed by session_id
  const [comments, setComments] = useState<Record<string, MentorComment[]>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [sending, setSending] = useState<Record<string, boolean>>({});

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getMentorSessions({ limit: 100 }) as any;
      const items: MentorSession[] = res?.data ?? res ?? [];
      setSessions(items);
      // Set default team tab to first unique team
      if (items.length > 0 && !teamFilter) {
        setTeamFilter(items[0].team_name ?? items[0].team_id);
      }
    } catch {
      toast.error("Could not load sessions. Check your connection.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Derive unique teams from sessions
  const teams = Array.from(
    new Map(sessions.map(s => [s.team_id, s.team_name ?? s.team_id])).entries()
  ).map(([id, name]) => ({ id, name }));

  const filteredSessions = sessions.filter(
    s => (s.team_name ?? s.team_id) === teamFilter
  );

  const loadComments = useCallback(async (sessionId: string) => {
    try {
      const res = await getSessionComments(sessionId);
      setComments(prev => ({ ...prev, [sessionId]: res ?? [] }));
    } catch {
      setComments(prev => ({ ...prev, [sessionId]: [] }));
    }
  }, []);

  async function send(sessionId: string) {
    const text = drafts[sessionId]?.trim();
    if (!text || text.length < 10) {
      toast.error("Comment must be at least 10 characters.");
      return;
    }
    setSending(prev => ({ ...prev, [sessionId]: true }));
    try {
      await apiAddComment(sessionId, text);
      setDrafts(prev => ({ ...prev, [sessionId]: "" }));
      await loadComments(sessionId);
      toast.success("Comment added — student will see it in their dashboard.");
    } catch {
      toast.error("Failed to post comment. Please try again.");
    } finally {
      setSending(prev => ({ ...prev, [sessionId]: false }));
    }
  }

  // Stats
  const total = sessions.length;
  const tipscDone = sessions.filter(s => s.tipsc_score != null).length;
  const dfvReady = sessions.filter(s => s.ready_for_dfv).length;
  const uniqueTeams = teams.length;

  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "mentor") return <Navigate to={user.role === "admin" ? "/admin" : "/workspace"} replace />;

  return (
    <div className="min-h-screen bg-muted/50">
      <header className="border-b bg-white">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-6">
            <Logos to="/mentor" />
            <p className="hidden text-sm font-semibold text-muted-foreground md:block">
              Mentor Dashboard &gt; <span className="text-primary font-bold">Team Progress Monitor</span>
            </p>
          </div>
          <div className="flex items-center gap-4">
            <p className="text-sm font-semibold">{user.name}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void logout()}
              className="flex items-center gap-1.5 text-primary border-primary/20 hover:bg-primary/5"
            >
              <LogOut className="h-4 w-4" /> Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Teams Assigned", uniqueTeams],
            ["Total Students", total],
            ["TIPSC Complete", tipscDone],
            ["DFV Ready", dfvReady],
          ].map(([label, value]) => (
            <Card key={label as string}>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="mt-2 text-3xl font-bold text-primary">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {loading ? (
          <div className="mt-20 flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="mt-12 text-center text-muted-foreground">
            <h2 className="text-xl font-semibold text-slate-800">No sessions found</h2>
            <p className="mt-2">When students on your team start sessions, they will appear here.</p>
          </div>
        ) : (
          <>
            {teams.length > 1 && (
              <SegmentedTabs
                className="mt-8 max-w-md"
                value={teamFilter}
                onValueChange={setTeamFilter}
                options={teams.map(t => ({ value: t.name, label: t.name }))}
              />
            )}

            <Card className="mt-6 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <thead className="bg-muted text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-4">Student</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">TIPSC</th>
                      <th className="p-4">DFV Ready</th>
                      <th className="p-4">Last Active</th>
                      <th className="p-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSessions.map((session) => (
                      <tr key={session.session_id} className="border-t bg-white">
                        <td className="p-4">
                          <p className="font-semibold">{session.student_name ?? "—"}</p>
                          <p className="text-xs text-muted-foreground">{session.team_name ?? session.team_id}</p>
                        </td>
                        <td className="p-4">
                          <StatusBadge
                            type={
                              session.status.includes("running") ? "in_progress"
                              : session.status.includes("completed") ? "completed"
                              : "available"
                            }
                            label={session.status.replace(/_/g, " ")}
                          />
                        </td>
                        <td className="p-4">
                          {session.tipsc_score != null ? (
                            <span className="font-bold text-emerald-700">{session.tipsc_score}/10</span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="p-4">
                          {session.ready_for_dfv == null ? (
                            <span className="text-muted-foreground">—</span>
                          ) : session.ready_for_dfv ? (
                            <StatusBadge type="completed" label="Yes" />
                          ) : (
                            <StatusBadge type="locked" label="No" />
                          )}
                        </td>
                        <td className="p-4 text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            {new Date(session.updated_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                          </span>
                        </td>
                        <td className="p-4">
                          {/* Comment Dialog */}
                          <Dialog onOpenChange={(open) => { if (open) loadComments(session.session_id); }}>
                            <DialogTrigger asChild>
                              <Button variant="secondary" size="sm">
                                <MessageSquare className="h-4 w-4" /> Comment
                              </Button>
                            </DialogTrigger>
                            <DialogContent>
                              <DialogHeader>
                                <DialogTitle>Comments for {session.student_name ?? "Student"}</DialogTitle>
                              </DialogHeader>

                              {/* Comment history */}
                              <div className="rounded-lg border p-4">
                                <h3 className="font-bold">Comment History</h3>
                                <div className="mt-3 max-h-48 space-y-3 overflow-y-auto">
                                  {(comments[session.session_id] ?? []).length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No comments yet.</p>
                                  ) : (
                                    (comments[session.session_id] ?? []).map((c) => (
                                      <div key={c.comment_id} className="rounded-lg bg-muted p-3 text-sm">
                                        <p className="font-semibold text-primary">
                                          {c.mentor_name} ·{" "}
                                          <span className="text-xs text-muted-foreground">
                                            {new Date(c.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                                          </span>
                                        </p>
                                        <p className="mt-1 text-slate-700">{c.comment}</p>
                                      </div>
                                    ))
                                  )}
                                </div>

                                {/* New comment input */}
                                <Textarea
                                  className="mt-4"
                                  value={drafts[session.session_id] ?? ""}
                                  onChange={(e) =>
                                    setDrafts(prev => ({ ...prev, [session.session_id]: e.target.value }))
                                  }
                                  placeholder="Add a mentor comment (min 10 characters)..."
                                />
                                <Button
                                  className="mt-3"
                                  variant="secondary"
                                  disabled={sending[session.session_id]}
                                  onClick={() => send(session.session_id)}
                                >
                                  {sending[session.session_id]
                                    ? <Loader2 className="h-4 w-4 animate-spin" />
                                    : <Send className="h-4 w-4" />}
                                  {sending[session.session_id] ? "Sending..." : "Send"}
                                </Button>
                              </div>
                            </DialogContent>
                          </Dialog>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
