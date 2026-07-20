import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Archive, Download, Target, TrendingUp, Users, Clock, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "@/components/ui/alert-dialog";
import { MentorChat } from "@/components/shared/MentorChat";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { Timeline } from "@/components/shared/Timeline";
import { isFlowRunning } from "@/hooks/useSessionPolling";
import { archiveSession as archiveSessionApi } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { downloadMarkdown, generateMarkdown } from "@/utils/exportMarkdown";
import { toast } from "sonner";
// NOTE: no backend endpoint exists yet for "list my teammates' progress".
// This section stays on local mock data until that route is added.
import { getStudents, Student } from "@/utils/adminData";
import { DetailedProgressView } from "@/components/shared/DetailedProgressView";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function StudentWorkspace() {
  const { user, sessionId, serverStatus, session, results, formData, timeline, archiveSession } = useAuth();
  const firstName = user?.name.split(" ")[0] || "Student";
  const running = serverStatus ? isFlowRunning(serverStatus) : false;

  // Polling for this session is already handled globally in WorkspaceLayout.tsx —
  // no need to poll again here.

  const teammates = useMemo<Student[]>(() => {
    if (!user || !user.teamId) return [];
    return getStudents().filter((s) => s.teamId === user.teamId);
  }, [user]);

  const modules = [
    { key: "tipsc" as const, title: "TIPSC Evaluation", icon: Target, color: "text-secondary", path: "/workspace/tipsc", description: "Assess timely, importance, profitable, and solvable strength." },
    { key: "dfv" as const, title: "DFV Analysis", icon: TrendingUp, color: "text-primary", path: "/workspace/dfv", description: "Validate desirability, feasibility, and viability before moving ahead." },
    { key: "discovery" as const, title: "Customer Discovery", icon: Users, color: "text-accent", path: "/workspace/discovery", description: "Generate customer jobs, interview plans, and discovery recommendations." }
  ];

  const exportReport = () => downloadMarkdown(generateMarkdown(results, formData), `agentic-ai-report-${Date.now()}.md`);

  async function handleArchive() {
    if (running) {
      toast.error("Cannot archive while a flow is running.");
      return;
    }
    if (sessionId) {
      try {
        await archiveSessionApi(sessionId);
      } catch (error) {
        toast.error("Failed to archive session on the server.");
        return;
      }
    }
    archiveSession();
    toast.success("Session archived. You can start a new session from TIPSC.");
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-primary">Welcome, {firstName}</h1>
          <p className="mt-1 text-muted-foreground">Move through TIPSC, DFV, and Customer Discovery in sequence.</p>
          {serverStatus && <p className="mt-1 text-xs text-muted-foreground">Session status: {serverStatus.replace(/_/g, " ")}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportReport}><Download className="h-4 w-4" /> Export</Button>
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="outline" disabled={running}><Archive className="h-4 w-4" /> Archive Session</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Archive this session?</AlertDialogTitle>
                <AlertDialogDescription>Archived sessions are preserved in history. You must archive before starting a new session.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => { exportReport(); void handleArchive(); }}>Download & Archive</AlertDialogAction>
                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => void handleArchive()}>Archive Without Saving</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      <div className="mt-8 grid grid-cols-3 gap-2 rounded-lg bg-white p-2 shadow-sm">
        {(["tipsc", "dfv", "discovery"] as const).map((key) => (
          <div key={key} className={`h-3 rounded-full ${session[key] === "completed" ? "bg-emerald-500" : session[key] === "locked" ? "bg-muted" : "bg-secondary"}`} />
        ))}
      </div>
      <div className="mt-8 grid gap-6 md:grid-cols-3">
        {modules.map(({ key, title, icon: Icon, color, path, description }) => {
          const status = session[key];
          return (
            <Card key={key}>
              <CardHeader>
                <Icon className={`h-9 w-9 ${color}`} />
                <CardTitle className="mt-3">{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <StatusBadge type={status} />
                <p className="mt-4 min-h-16 text-sm text-muted-foreground">{description}</p>
                {status === "locked" ? (
                  <p className="mt-4 rounded-lg bg-muted p-3 text-sm font-semibold text-muted-foreground">Complete the prior framework to unlock.</p>
                ) : (
                  <Button asChild className="mt-4 w-full" variant={status === "completed" ? "outline" : "secondary"}>
                    <Link to={path}>{status === "completed" ? "View Results" : status === "in_progress" ? "Continue" : "Start"}</Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
      <div className="mt-8 rounded-lg border border-secondary/20 bg-secondary/10 p-4 text-sm font-semibold text-secondary">
        Sequential Evaluation: TIPSC unlocks DFV, and DFV unlocks Customer Discovery.
      </div>

      {/* Team Progress Monitor — mock data until a real "my team" endpoint exists */}
      {user?.teamId && teammates.length > 0 && (
        <Card className="mt-8 overflow-hidden">
          <CardHeader>
            <CardTitle>Team Progress Monitor</CardTitle>
            <p className="text-xs text-muted-foreground">Monitor progress for members of your team.</p>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="bg-muted text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-4">Student</th>
                    <th className="p-4">TIPSC</th>
                    <th className="p-4">DFV</th>
                    <th className="p-4">JTBD</th>
                    <th className="p-4">Last Active</th>
                    <th className="p-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {teammates.map((student) => (
                    <tr key={student.srn} className="border-t bg-white">
                      <td className="p-4">
                        <p className="font-semibold">{student.name}</p>
                        <p className="text-muted-foreground text-xs">
                          {student.srn} {student.srn === user.srn && <span className="ml-1 text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">You</span>}
                        </p>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          {Object.values(student.tips || {}).map((score, i) => (
                            <TrafficDot key={i} status={score.status} />
                          ))}
                        </div>
                      </td>
                      <td className="p-4">
                        {student.dfv === "Pending" ? (
                          <StatusBadge type="available" label="Pending" />
                        ) : (
                          <span className={student.dfv === "GO" ? "font-bold text-emerald-700" : "font-bold text-red-700"}>
                            {student.dfv}
                          </span>
                        )}
                      </td>
                      <td className="p-4">
                        {student.jtbd ? <StatusBadge type="completed" /> : <StatusBadge type="locked" label="Pending" />}
                      </td>
                      <td className="p-4 text-muted-foreground">
                        <span className="flex items-center gap-1 text-xs">
                          <Clock className="h-4 w-4" />
                          {student.lastActive}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button variant="outline" size="sm">
                                <Eye className="h-4 w-4 mr-1" /> View
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle>{student.name}</DialogTitle>
                              </DialogHeader>
                              <DetailedProgressView student={student} />
                            </DialogContent>
                          </Dialog>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Activity Timeline</CardTitle></CardHeader><CardContent><Timeline events={timeline} /></CardContent></Card>
        <Card><CardHeader><CardTitle>Mentor Comments</CardTitle></CardHeader><CardContent><MentorChat sessionId={sessionId} /></CardContent></Card>
      </div>
    </main>
  );
}