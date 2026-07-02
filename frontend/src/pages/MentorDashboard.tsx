import { useMemo, useState } from "react";
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
import { mockMentorMessages, mockMentorTeams } from "@/data/mockData";
import { useAuth } from "@/context/AuthContext";

export function MentorDashboard() {
  const { user, logout } = useAuth();
  const [team, setTeam] = useState(mockMentorTeams[0].name);
  const [comments, setComments] = useState<Record<string, { sender: string; message: string; timestamp: string }[]>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const selected = mockMentorTeams.find((item) => item.name === team) || mockMentorTeams[0];
  const stats = useMemo(() => {
    const members = mockMentorTeams.flatMap((item) => item.members);
    return [
      ["Teams Assigned", mockMentorTeams.length],
      ["Total Students", members.length],
      ["TIPS Complete", members.filter((m) => Object.values(m.tips).every((s) => s.status === "green")).length],
      ["DFV Complete", members.filter((m) => m.dfv !== "Pending").length]
    ];
  }, []);
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "mentor") return <Navigate to={user.role === "admin" ? "/admin" : "/workspace"} replace />;

  function send(srn: string) {
    const text = drafts[srn]?.trim();
    if (!text) return;
    setComments((current) => ({
      ...current,
      [srn]: [...(current[srn] || []), { sender: user?.name || "Mentor", message: text, timestamp: "Just now" }]
    }));
    setDrafts((current) => ({ ...current, [srn]: "" }));
    toast.success("Remark added");
  }

  return (
    <div className="min-h-screen bg-muted/50">
      <header className="bg-primary text-primary-foreground">
        <div className="mx-auto flex min-h-20 max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-6">
            <Logos to="/mentor" invert />
            <div><p className="text-sm text-white/70">Mentor Dashboard</p><h1 className="text-xl font-bold">Team Progress Monitor</h1></div>
          </div>
          <div className="flex items-center gap-3">
            <p className="text-sm font-semibold">{user.name}</p>
            <Button variant="outline" className="border-white/30 bg-white/10 text-white hover:bg-white/20" onClick={() => void logout()}><LogOut className="h-4 w-4" /> Logout</Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          {stats.map(([label, value]) => (
            <Card key={label}><CardContent className="p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-bold text-primary">{value}</p></CardContent></Card>
          ))}
        </div>
        <SegmentedTabs className="mt-8 max-w-md" value={team} onValueChange={setTeam} options={mockMentorTeams.map((item) => ({ value: item.name, label: item.name }))} />
        <Card className="mt-6 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="bg-muted text-xs uppercase text-muted-foreground">
                <tr><th className="p-4">Student</th><th className="p-4">TIPS</th><th className="p-4">DFV</th><th className="p-4">JTBD</th><th className="p-4">Last Active</th><th className="p-4">Actions</th></tr>
              </thead>
              <tbody>
                {selected.members.map((student) => (
                  <tr key={student.srn} className="border-t bg-white">
                    <td className="p-4"><p className="font-semibold">{student.name}</p><p className="text-muted-foreground">{student.srn}</p></td>
                    <td className="p-4"><div className="flex gap-2">{Object.values(student.tips).map((score, i) => <TrafficDot key={i} status={score.status} />)}</div></td>
                    <td className="p-4">{student.dfv === "Pending" ? <StatusBadge type="available" label="Pending" /> : <span className={student.dfv === "GO" ? "font-bold text-emerald-700" : "font-bold text-red-700"}>{student.dfv}</span>}</td>
                    <td className="p-4">{student.jtbd ? <StatusBadge type="completed" /> : <StatusBadge type="locked" label="Pending" />}</td>
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
                              <div className="mt-3 space-y-3">
                                {[...mockMentorMessages, ...(comments[student.srn] || [])].map((comment, i) => (
                                  <div key={`${comment.timestamp}-${i}`} className="rounded-lg bg-muted p-3 text-sm">
                                    <p className="font-semibold">{comment.sender} · <span className="text-muted-foreground">{comment.timestamp}</span></p>
                                    <p className="mt-1 text-muted-foreground">{comment.message}</p>
                                  </div>
                                ))}
                              </div>
                              <Textarea className="mt-4" value={drafts[student.srn] || ""} onChange={(e) => setDrafts({ ...drafts, [student.srn]: e.target.value })} placeholder="Add a mentor remark..." />
                              <Button className="mt-3" variant="secondary" onClick={() => send(student.srn)}><Send className="h-4 w-4" /> Send</Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </div>
  );
}
