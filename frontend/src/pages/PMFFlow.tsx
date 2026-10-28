import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Loader2, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { triggerPmf, getSession } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export function PMFFlow() {
  const { session, sessionId, serverStatus, results, sessionDoc, setSessionFromServer, addEvent } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const running = submitting || serverStatus === "pmf_waiting" || serverStatus === "pmf_running";
  const data: any = results.pmf?.output || results.pmf;
  const score = data?.pmf_score ?? data?.pmf_metrics?.pmf_score;
  const risks: string[] = data?.key_risks || data?.risk_assessment?.key_risks || [];

  async function run() {
    if (!sessionId || running) return;
    setSubmitting(true);
    try {
      await triggerPmf(sessionId);
      setSessionFromServer(await getSession(sessionId));
      addEvent("PMF analysis started");
    } catch (err: any) {
      toast.error(err?.message || "Could not start PMF analysis.");
    } finally { setSubmitting(false); }
  }

  if (session.pmf === "locked") return <Navigate to="/workspace" replace />;
  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-3xl font-bold">Product-Market Fit Analysis</h1>
        <Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button>
      </div>
      {serverStatus === "pmf_failed" && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        {sessionDoc?.failure_metadata?.error_message || "PMF analysis failed. Your previous stages are saved; you can retry."}
      </div>}
      {running ? <Card><CardContent className="flex items-center gap-3 p-10"><Loader2 className="animate-spin" /> Evaluating your project and previous analyses…</CardContent></Card> : data ? <>
        <Card><CardHeader><CardTitle>{data.verdict || "PMF assessment"}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-4xl font-bold">{score == null ? "Insufficient evidence" : `${score}/100`}</p>
            <p className="text-sm text-muted-foreground">Qualitative assessment; customer metrics require measured survey and retention data.</p>
            <p>{data.executive_summary || ""}</p>
          </CardContent>
        </Card>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ["Sean Ellis Test", data.sean_ellis_test?.analysis],
            ["Net Promoter Score", data.net_promoter_score?.promoters_ratio],
            ["Retention", data.retention_analysis?.summary],
          ].map(([label, summary]) => <Card key={label}><CardHeader><CardTitle className="text-base">{label}</CardTitle></CardHeader>
            <CardContent><p className="font-semibold">Not measured</p><p className="mt-2 text-sm text-muted-foreground">{summary || "Customer evidence has not been supplied."}</p></CardContent></Card>)}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {[["Customer alignment", data.target_customer_alignment], ["Demand", data.demand_validation],
            ["Value proposition", data.value_proposition_strength], ["Defensibility", data.defensibility_and_moat]].map(([label, evidence]: any) =>
            evidence && <Card key={label}><CardHeader><CardTitle className="text-base">{label}</CardTitle></CardHeader><CardContent>{evidence.summary}</CardContent></Card>)}
        </div>
        {!!data.key_strengths?.length && <Card><CardHeader><CardTitle>Strengths</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-2 pl-5">{data.key_strengths.map((item: string, i: number) => <li key={i}>{item}</li>)}</ul></CardContent></Card>}
        {!!risks.length && <Card><CardHeader><CardTitle>Risks and evidence gaps</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-2 pl-5">{risks.map((item, i) => <li key={i}>{item}</li>)}</ul></CardContent></Card>}
      </> : <Card><CardContent className="space-y-3 p-8"><BarChart3 /><p>Assess your idea using the TIPSC, DFV and customer discovery results. Unmeasured customer metrics will be marked as unavailable.</p></CardContent></Card>}
      <Button onClick={run} disabled={!sessionId || running}>{running ? "Analysis in progress" : data ? "Re-run PMF Analysis" : serverStatus === "pmf_failed" ? "Retry PMF Analysis" : "Run PMF Analysis"}</Button>
    </main>
  );
}
