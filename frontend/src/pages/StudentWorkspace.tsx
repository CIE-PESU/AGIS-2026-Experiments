import { Link } from "react-router-dom";
import { Archive, Download, Target, TrendingUp, Users } from "lucide-react";
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
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Timeline } from "@/components/shared/Timeline";
import { deriveStageAccess, isFlowRunning, useSessionPolling } from "@/hooks/useSessionPolling";
import { archiveSession as archiveSessionApi } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { downloadMarkdown, generateMarkdown } from "@/utils/exportMarkdown";
import { toast } from "sonner";

export function StudentWorkspace() {
  const { user, sessionId, serverStatus, session, results, formData, timeline, archiveSession, setSessionFromServer } = useAuth();
  const firstName = user?.name.split(" ")[0] || "Student";
  const running = serverStatus ? isFlowRunning(serverStatus) : false;

  useSessionPolling(sessionId, setSessionFromServer, Boolean(sessionId));

  const modules = [
    { key: "tipsc" as const, title: "TIPS Evaluation", icon: Target, color: "text-secondary", path: "/workspace/tipsc", description: "Assess timing, idea, problem, solution, and competition readiness." },
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
      } catch {
        toast.message("Archive saved locally — backend unavailable.");
      }
    }
    archiveSession();
    toast.success("Session archived. You can start a new session from TIPS.");
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-primary">Welcome, {firstName}</h1>
          <p className="mt-1 text-muted-foreground">Move through TIPS, DFV, and Customer Discovery in sequence.</p>
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
        Sequential Evaluation: TIPS unlocks DFV, and DFV unlocks Customer Discovery.
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Activity Timeline</CardTitle></CardHeader><CardContent><Timeline events={timeline} /></CardContent></Card>
        <Card><CardHeader><CardTitle>Mentor Comments</CardTitle></CardHeader><CardContent><MentorChat sessionId={sessionId} /></CardContent></Card>
      </div>
    </main>
  );
}
