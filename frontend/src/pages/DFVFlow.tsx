import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { CheckCircle2, DollarSign, Heart, Loader2, ThumbsDown, ThumbsUp, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { TrafficDot } from "@/components/shared/StatusBadge";
import { DFV_CONTEXT_MIN, USE_MOCK_FLOWS } from "@/constants";
import { runDFVAnalysis } from "@/services/api";
import { triggerDfv } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import type { DFVResult } from "@/data/mockData";
import { toast } from "sonner";

export function DFVFlow() {
  const { session, sessionId, results, saveResults, unlockNext, addEvent } = useAuth();
  const [phase, setPhase] = useState<"form" | "processing" | "results">(results.dfv ? "results" : "form");
  const [result, setResult] = useState<DFVResult | null>(results.dfv);
  const [inputs, setInputs] = useState({ desirability_context: "", feasibility_context: "", viability_context: "" });
  if (session.dfv === "locked") return <Navigate to="/workspace" replace />;
  async function run() {
    const payload = {
      desirability_context: inputs.desirability_context.trim(),
      feasibility_context: inputs.feasibility_context.trim(),
      viability_context: inputs.viability_context.trim()
    };
    if (Object.values(payload).some((value) => value.length < DFV_CONTEXT_MIN)) {
      toast.error(`Each DFV context field must be at least ${DFV_CONTEXT_MIN} characters.`);
      return;
    }
    setPhase("processing");
    addEvent("DFV Triggered");
    try {
      if (sessionId) await triggerDfv(sessionId, payload);
    } catch {
      if (!USE_MOCK_FLOWS) {
        setPhase("form");
        return;
      }
    }
    const data = await runDFVAnalysis();
    setResult(data);
    saveResults("dfv", data);
    unlockNext("dfv");
    addEvent("DFV Analysis Completed");
    setPhase("results");
  }
  const sections = [
    ["desirability_context", Heart, "text-accent", "Who wants this, and why now?"],
    ["feasibility_context", Wrench, "text-secondary", "What can your team build and operate?"],
    ["viability_context", DollarSign, "text-primary", "How does this become sustainable?"]
  ] as const;
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Header title="DFV Analysis" />
      {phase === "form" && <Card><CardContent className="space-y-6 p-6">
        {sections.map(([key, Icon, color, prompt]) => <label key={key} className="block"><span className="flex items-center gap-2 font-semibold capitalize"><Icon className={`h-5 w-5 ${color}`} /> {key}</span><span className="mt-1 block text-sm text-muted-foreground">{prompt}</span><Textarea className="mt-2" value={inputs[key]} onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })} /></label>)}
        <Button variant="secondary" disabled={!Object.values(inputs).every(Boolean)} onClick={run}>Run DFV Analysis</Button>
      </CardContent></Card>}
      {phase === "processing" && <Card><CardContent className="space-y-6 p-10">{sections.map(([key]) => <div key={key}><div className="mb-2 flex items-center justify-between text-sm font-semibold capitalize"><span>{key} Agent</span><Loader2 className="h-4 w-4 animate-spin" /></div><div className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full w-2/3 animate-pulse rounded-full bg-secondary" /></div></div>)}</CardContent></Card>}
      {phase === "results" && result && <Card><CardHeader><CardTitle>DFV Results</CardTitle></CardHeader><CardContent>
        <div className={`rounded-lg p-5 ${result.decision === "GO" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
          <div className="flex items-center gap-2 text-xl font-bold">{result.decision === "GO" ? <ThumbsUp /> : <ThumbsDown />} {result.decision}</div>
          <p className="mt-2 text-sm">{result.executiveSummary}</p>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">{Object.entries(result.dimensions).map(([key, value]) => <div key={key} className="rounded-lg border p-4"><div className="flex items-center gap-2"><TrafficDot status={value.status} /><h3 className="font-bold capitalize">{key}</h3></div><p className="mt-3 text-sm text-muted-foreground">{value.summary}</p><ul className="mt-3 space-y-2 text-sm">{value.details.map((d) => <li key={d} className="flex gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{d}</li>)}</ul></div>)}</div>
        <h3 className="mt-6 font-bold">Recommendations</h3><ol className="mt-3 space-y-2 text-sm">{result.recommendations.map((rec, i) => <li key={rec}>{i + 1}. {rec}</li>)}</ol>
      </CardContent></Card>}
    </main>
  );
}

function Header({ title }: { title: string }) {
  return <div className="mb-8 flex flex-wrap items-center justify-between gap-3"><h1 className="text-3xl font-bold text-primary">{title}</h1><Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button></div>;
}
