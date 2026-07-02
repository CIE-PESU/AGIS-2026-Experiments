import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { CheckCircle2, Loader2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { generateJTBD } from "@/services/api";
import { triggerDiscovery } from "@/services/authSessions";
import { USE_MOCK_FLOWS } from "@/constants";
import { useAuth } from "@/context/AuthContext";
import type { JTBDResult } from "@/data/mockData";

export function DiscoveryFlow() {
  const { session, sessionId, results, saveResults, unlockNext, addEvent } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JTBDResult | null>(results.discovery);
  if (session.discovery === "locked") return <Navigate to="/workspace" replace />;

  async function startDiscovery() {
    setLoading(true);
    addEvent("Discovery Triggered");
    try {
      if (sessionId) await triggerDiscovery(sessionId);
    } catch {
      if (!USE_MOCK_FLOWS) {
        setLoading(false);
        return;
      }
    }
    const data = await generateJTBD();
    setResult(data);
    saveResults("discovery", data);
    unlockNext("discovery");
    addEvent("Discovery Completed");
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-primary">Customer Discovery</h1>
        <Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button>
      </div>
      {!result && !loading && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <p className="text-muted-foreground">Trigger the discovery planner when DFV is complete. The backend queues the flow via POST /sessions/&#123;id&#125;/trigger/discovery.</p>
            <Button variant="secondary" onClick={() => void startDiscovery()}>Trigger Discovery Planner</Button>
          </CardContent>
        </Card>
      )}
      {loading && <Card className="border-accent/20"><CardContent className="flex min-h-72 flex-col items-center justify-center gap-4 p-10 text-center text-accent"><Users className="h-14 w-14 animate-pulse" /><Loader2 className="h-6 w-6 animate-spin" /><p className="font-semibold">Discovery agent is generating customer jobs and interviews...</p></CardContent></Card>}
      {result && <div className="space-y-6">
        <Card><CardHeader><CardTitle>Customer Jobs</CardTitle></CardHeader><CardContent className="grid gap-4 md:grid-cols-2">{result.jobs.map((job) => <div key={job.title} className="rounded-lg border p-4"><h3 className="font-bold">{job.title}</h3><p className="mt-2 text-sm text-muted-foreground">{job.context}</p><p className="mt-2 text-sm font-semibold text-secondary">Outcome: {job.outcome}</p></div>)}</CardContent></Card>
        <Card><CardHeader><CardTitle>Interview Plan</CardTitle></CardHeader><CardContent><p className="text-muted-foreground">{result.interviewPlan.objective}</p><div className="mt-5 grid gap-4 md:grid-cols-2"><div><h3 className="font-bold">Target Segments</h3><div className="mt-3 space-y-2">{result.interviewPlan.targetSegments.map((s) => <p key={s} className="flex gap-2 text-sm"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{s}</p>)}</div></div><div><h3 className="font-bold">Questions</h3><ol className="mt-3 space-y-2 text-sm">{result.interviewPlan.questions.map((q, i) => <li key={q}>{i + 1}. {q}</li>)}</ol><p className="mt-4 text-sm font-semibold">Sample size: {result.interviewPlan.sampleSize}</p></div></div></CardContent></Card>
        <Card><CardHeader><CardTitle>Recommendations</CardTitle></CardHeader><CardContent><ol className="space-y-2 text-sm">{result.recommendations.map((rec, i) => <li key={rec}>{i + 1}. {rec}</li>)}</ol></CardContent></Card>
      </div>}
    </main>
  );
}
