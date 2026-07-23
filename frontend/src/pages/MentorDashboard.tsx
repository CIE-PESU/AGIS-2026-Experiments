import { useMemo, useState, useCallback, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { Clock, Eye, LogOut, MessageSquare, Send } from "lucide-react";
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
import { getTeamsWithMembers, getComments, addComment, Comment, getMentors } from "@/utils/adminData";

import { deriveStageAccess } from "@/hooks/useSessionPolling";

export function MentorDashboard() {
  const { user, logout } = useAuth();
  const [loadedTeams, setLoadedTeams] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      if (!user || user.role !== "mentor") return;
      const allMentors = await getMentors();
      const currentMentor = allMentors.find(m => m.srn?.toLowerCase() === user.srn.toLowerCase());
      
      if (!currentMentor) {
        setLoadedTeams([]);
        return;
      }
      
      const allTeams = await getTeamsWithMembers();
      setLoadedTeams(allTeams.filter(t => t.mentorId === currentMentor.id));
    }
    loadData();
  }, [user]);

  const [team, setTeam] = useState("");
  useEffect(() => {
    if (loadedTeams.length > 0 && !team) {
      setTeam(loadedTeams[0].name);
    }
  }, [loadedTeams, team]);

  const [comments, setComments] = useState<Record<string, Comment[]>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const selected = loadedTeams.find((item) => item.name === team) || loadedTeams[0] || { name: "", members: [] };

  const refreshComments = useCallback(async () => {
    const allComments: Record<string, Comment[]> = {};
    const students = loadedTeams.flatMap(t => t.members);
    await Promise.all(students.map(async (s) => {
      if (s.sessionId) {
        allComments[s.srn] = await getComments(s.sessionId);
      } else {
        allComments[s.srn] = [];
      }
    }));
    setComments(allComments);
  }, [loadedTeams]);

  useEffect(() => {
    refreshComments();
  }, [refreshComments]);

  const stats = useMemo(() => {
    const members = loadedTeams.flatMap((item) => item.members);
    return [
      ["Teams Assigned", loadedTeams.length],
      ["Total Students", members.length],
      ["TIPSC Complete", members.filter((m) => Object.keys(m.tips).length > 0 && Object.values(m.tips).every((s: any) => s.status === "green")).length],
      ["DFV Complete", members.filter((m) => m.dfv !== "Pending").length]
    ];
  }, [loadedTeams]);

  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "mentor") return <Navigate to={user.role === "admin" ? "/admin" : "/workspace"} replace />;

  async function send(srn: string, sessionId?: string | null) {
    if (!sessionId) {
      toast.error("Student hasn't started a session yet");
      return;
    }
    const text = drafts[srn]?.trim();
    if (!text) return;
    
    try {
      await addComment(sessionId, text);
      setDrafts((current) => ({ ...current, [srn]: "" }));
      await refreshComments();
      toast.success("Remark added");
    } catch (err: any) {
      toast.error(err.message);
    }
  }

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
        <div className="grid gap-4 md:grid-cols-4">
          {stats.map(([label, value]) => (
            <Card key={label}><CardContent className="p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-bold text-primary">{value}</p></CardContent></Card>
          ))}
        </div>

        {loadedTeams.length === 0 ? (
          <div className="mt-12 text-center text-muted-foreground">
            <h2 className="text-xl font-semibold text-slate-800">No teams assigned yet</h2>
            <p className="mt-2">When an admin assigns teams to you, their progress will appear here.</p>
          </div>
        ) : (
          <>
            <SegmentedTabs className="mt-8 max-w-md" value={team} onValueChange={setTeam} options={loadedTeams.map((item) => ({ value: item.name, label: item.name }))} />
            <Card className="mt-6 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="bg-muted text-xs uppercase text-muted-foreground">
                <tr><th className="p-4">Student</th><th className="p-4">TIPSC</th><th className="p-4">DFV</th><th className="p-4">JTBD</th><th className="p-4">Last Active</th><th className="p-4">Actions</th></tr>
              </thead>
              <tbody>
                {selected.members.map((student: any) => {
                  const access = deriveStageAccess(student);
                  return (
                    <tr key={student.srn} className="border-t bg-white">
                      <td className="p-4"><p className="font-semibold">{student.name}</p><p className="text-muted-foreground">{student.srn}</p></td>
                      <td className="p-4">
                        {access.tipsc === "in_progress" ? (
                          <StatusBadge type="in_progress" />
                        ) : (
                          <div className="flex gap-2">{Object.values(student.tips || {}).map((score: any, i) => <TrafficDot key={i} status={score.status} />)}</div>
                        )}
                      </td>
                      <td className="p-4">
                        {access.dfv === "locked" ? (
                          <StatusBadge type="locked" />
                        ) : access.dfv === "in_progress" ? (
                          <StatusBadge type="processing" label="Running" />
                        ) : access.dfv === "available" ? (
                          <StatusBadge type="available" label="Pending" />
                        ) : access.dfv === "failed" ? (
                          <StatusBadge type="failed" label="Failed" />
                        ) : (
                          <span className={student.dfv === "GO" ? "font-bold text-emerald-700" : student.dfv === "NO-GO" ? "font-bold text-red-700" : "font-semibold text-slate-700"}>{student.dfv}</span>
                        )}
                      </td>
                      <td className="p-4">
                        {access.discovery === "locked" ? (
                          <StatusBadge type="locked" />
                        ) : access.discovery === "in_progress" ? (
                          <StatusBadge type="processing" label="Running" />
                        ) : access.discovery === "completed" ? (
                          <StatusBadge type="completed" />
                        ) : access.discovery === "failed" ? (
                          <StatusBadge type="failed" label="Failed" />
                        ) : (
                          <StatusBadge type="available" label="Pending" />
                        )}
                      </td>
                    <td className="p-4 text-muted-foreground"><span className="flex items-center gap-1"><Clock className="h-4 w-4" />{student.lastActive}</span></td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <Dialog>
                          <DialogTrigger asChild><Button variant="outline" size="sm"><Eye className="h-4 w-4" /> View</Button></DialogTrigger>
                          <DialogContent><DialogHeader><DialogTitle>{student.name}</DialogTitle></DialogHeader><DetailedProgressView student={student} /></DialogContent>
                        </Dialog>
                        <Dialog>
                          <DialogTrigger asChild><Button variant="secondary" size="sm"><MessageSquare className="h-4 w-4" /> Comment</Button></DialogTrigger>
                          <DialogContent>
                            <DialogHeader><DialogTitle>Remarks for {student.name}</DialogTitle></DialogHeader>
                            <DetailedProgressView student={student} />
                            <div className="rounded-lg border p-4">
                              <h3 className="font-bold">Comment History</h3>
                              <div className="mt-3 space-y-3 max-h-48 overflow-y-auto">
                                {(comments[student.srn] || []).map((comment, i) => (
                                  <div key={`${comment.timestamp}-${i}`} className="rounded-lg bg-muted p-3 text-sm">
                                    <p className="font-semibold text-primary">{comment.sender} · <span className="text-muted-foreground text-xs">{comment.timestamp}</span></p>
                                    <p className="mt-1 text-slate-700">{comment.message}</p>
                                  </div>
                                ))}
                              </div>
                              <Textarea className="mt-4" value={drafts[student.srn] || ""} onChange={(e) => setDrafts({ ...drafts, [student.srn]: e.target.value })} placeholder="Add a mentor remark..." />
                              <Button className="mt-3" variant="secondary" onClick={() => send(student.srn, student.sessionId)} disabled={!student.sessionId} title={!student.sessionId ? "Student has not started a session yet" : ""}><Send className="h-4 w-4" /> Send</Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </td>
                  </tr>
                );
                  })}
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
